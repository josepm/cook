"""
generate cli args for multi_keys
runs on desktop from cook
"""


import json
import os
import sys
import pandas as pd
from calendar import monthrange
import numpy as np
import logging
logging.getLogger("airpy").setLevel(logging.CRITICAL)
import airpy as ap

from capacity_planning.utilities.temp_utils import TempUtils
from capacity_planning import sys_utils as s_ut

DO_MP = False
DEBUG = False

FILE_PATH = os.path.dirname(os.path.abspath(__file__))


def get_week_values(idx_, i_dt, fst_, cnt_):          #  monday to sunday
    # weeks always start on Monday and end on Sunday
    # fst_monday = first monday after _start
    _init_ = fst_ + pd.to_timedelta(7 * (idx_ - 1), unit='D')       # start of group: a monday (included)
    _end_ = _init_ + pd.to_timedelta(cnt_ * 7 - 1, unit='D')           # end of  group: a sunday (included)
    _days_ = (_end_ - i_dt).days                                    # days from issue date to _end_
    return _end_, _init_, _days_


def get_month_values(idx_, i_dt, fst_, cnt_):
    # fst_mont: first month after _start or including _start if _start os the first of the month
    next_m = fst_ + pd.to_timedelta(cnt_ * (idx_ - 1), unit='M')
    _, md = monthrange(next_m.year, next_m.month)
    _end_ = pd.to_datetime(str(next_m.year) + '-' + str(next_m.month) + '-' + str(md))  # horizon: end of the month after the issue date month
    _init_ = pd.to_datetime(str(next_m.year) + '-' + str(next_m.month) + '-01')
    _days_ = (_end_ - i_dt).days                                                # days from issue date to _date
    return _end_, _init_, _days_


def get_day_values(idx_, i_dt, fst_day, cnt_):
    _init_ = fst_day + pd.to_timedelta(cnt_ * (idx_ - 1), unit='D')       # start of  group: a monday (included)
    _end_ = _init_ + pd.to_timedelta(cnt_ - 1, unit='D')           # end of  group: a sunday (included)
    _days_ = (_end_ - i_dt).days                                    # days from issue date to _end_
    return _end_, _init_, _days_


def get_values(idx_, i_dt, fst, freq, cnt_):
    if 'M' in freq:
        return get_month_values(idx_, i_dt, fst, cnt_)
    elif 'W' in freq:
        return get_week_values(idx_, i_dt, fst, cnt_)
    elif 'D' in freq:
        return get_day_values(idx_, i_dt, fst, cnt_)
    else:
        return None


def run(argv):
    # cfg_file = os.path.join(FILE_PATH, 'config/wh_agents_cfg.json')
    s_ut.my_print('******* launching multi__keys *********')

    if len(argv) >= 2:
        cfg_file = os.path.join(FILE_PATH, argv[1])
    else:
        s_ut.my_print('ERROR in multi_keys: ' + str(sys.argv))
        sys.exit(0)

    with open(cfg_file, 'r') as fp:
        d_cfg = json.load(fp)

    cli_file = d_cfg['cli_file']

    if len(argv) == 3:
        issue_date_str = argv[2]
    else:
        issue_date_str = d_cfg.get('issue_date', None)        # fcast issue date
    if issue_date_str is None:
        s_ut.my_print('pid: ' + str(os.getpid()) + ' invalid arguments:issue_date missing')
        raise RuntimeError('failure')

    is_fcast = d_cfg['is_fcast']
    # when is_fcast is true, compute from issue_date + 1 included up to fcast_date = issue_date + periods included and report on groups of size group_days
    # when is_fcast is false, compute from issue_date - periods included up to issue_date included andreport on groups of size group_days
    freq = d_cfg.get("freq", None)
    if freq is None:
        s_ut.my_print('pid: ' + str(os.getpid()) + ' invalid arguments: freq missing')
        raise RuntimeError('failure')
    periods = d_cfg.get('periods', None)  # number of periods in units of freq
    if periods is None:
        s_ut.my_print('pid: ' + str(os.getpid()) + ' invalid arguments: periods missing')
        raise RuntimeError('failure')
    in_table = d_cfg.get('in_table', None)
    if in_table is None:
        s_ut.my_print('pid: ' + str(os.getpid()) + ' invalid arguments: in_table missing')
        raise RuntimeError('failure')
    key_lbl = d_cfg.get('key_lbl', None)
    if key_lbl is None:
        s_ut.my_print('pid: ' + str(os.getpid()) + ' invalid arguments:key_lbl missing')
        raise RuntimeError('failure')

    week_start = d_cfg.get('week_start', 0) % 7      # 0 monday, 1 tues, ...

    if is_fcast is True:
        run_agents(in_table, issue_date_str, periods, freq, key_lbl, week_start, cli_file)
    elif is_fcast is False:
        run_tickets(in_table, issue_date_str, periods, freq, key_lbl, week_start, cli_file)
    else:
        s_ut.my_print('ERROR: is_fcast not set')
        sys.exit(0)


def run_agents(in_table, issue_date_str, periods, freq, key_lbl, week_start, cli_file):
    qidt = 'select count(*) as rows from ' + in_table + ' where idt = \'' + issue_date_str + '\';'
    s_ut.my_print('issue date query: ' + qidt)
    idt_cnt_df = ap.presto(qidt, use_cache=False)
    if idt_cnt_df.loc[0, 'rows'] == 0:
        s_ut.my_print('FAILURE no data available for ' + issue_date_str)
        raise RuntimeError('failure')
    issue_date = pd.to_datetime(issue_date_str)

    # fcast_date
    fcast_date = pd.to_datetime(issue_date + pd.to_timedelta(periods, unit=freq))
    fcast_date_str = str(fcast_date.date())
    qfdt = 'select count(*) as rows from ' + in_table + ' where fdt >= \'' + fcast_date_str + '\';'
    s_ut.my_print(qfdt)
    fdt_cnt_df = ap.presto(qfdt, use_cache=False)
    if fdt_cnt_df.loc[0, 'rows'] == 0:
        s_ut.my_print('FAILURE no forecasts available for ' + issue_date)
        raise RuntimeError('failure')

    # fcast_start
    fcast_start = pd.to_datetime(issue_date) + pd.to_timedelta(1, unit='D')  # official start

    # key_lbl
    qklbl = 'select count(*) as rows from ' + in_table + ' where key_lbl >= \'' + key_lbl + '\';'
    s_ut.my_print(qklbl)
    klbl_cnt_df = ap.presto(qklbl, use_cache=False)
    if klbl_cnt_df.loc[0, 'rows'] == 0:
        s_ut.my_print('FAILURE no forecasts available for ' + issue_date)
        raise RuntimeError('failure')

    s_ut.my_print('input dates:::::\nweek_start (0 = Monday, 1 = Tuesday, ...): ' + str(week_start) +
                  ' fcast_date: ' + str(fcast_date.date()) +
                  ' issue_date: ' + str(issue_date.date()) +
                  ' fcast_start: ' + str(fcast_start.date()) +
                  ' key_lbl: ' + key_lbl)

    # adjust group fcast days and set the first fcast_start date, eg to first monday after issue date
    cnt = int(freq[:-1]) if len(freq) > 1 else 1
    if 'M' in freq:
        days_per_month = 365.25 / 12.0
        group_days = int(cnt * days_per_month)
        if fcast_start.day == 1:
            first = fcast_start
        else:
            dt_next = issue_date + pd.to_timedelta(1, unit='M')
            first = pd.to_datetime(str(dt_next.year) + '-' + str(dt_next.month) + '-01')
        prev = first - pd.to_timedelta(1, unit='M')
    elif 'W' in freq:
        group_days = cnt * 7
        diff = (week_start - fcast_start.weekday()) % 7
        first = fcast_start + pd.to_timedelta(diff, unit='D')     # first: first fcast_start date with first > issue_date AND first >= fcast_start > sssue_date
        prev = fcast_start + pd.to_timedelta(diff, unit='D') - pd.to_timedelta(14, unit='D')  # start of last complete week that ends on or before issue_date
    elif 'D' in freq:
        group_days = cnt
        first = fcast_start
        prev = first - pd.to_timedelta(1, unit='D')
    else:
        s_ut.my_print('FAILURE multi_agents::invalid freq: ' + str(freq))
        raise RuntimeError('failure')

    if first > fcast_date:
        s_ut.my_print('FAILURE first fcast start incompatible with input dates: : ' + str(first.date()))
        raise RuntimeError('failure')

    days_to_fcast = (fcast_date - prev).days          # to have a full week of actuals and baseline
    n_fcast = np.ceil(days_to_fcast / group_days)   # always the floor which will always include fcast_date. ceil may not
    end_dates = list()
    main_key = issue_date_str + '+' + fcast_date_str + '+' + key_lbl + '+' + str(group_days) + '+'   # + l_id + '+'
    cli_list = []
    for idx in range(1, int(n_fcast) + 5):        # set group of fcast dates that are reported together
        fcast_end, fcast_init, fcast_days = get_values(idx, issue_date, prev, freq, cnt)
        if fcast_init >= issue_date and fcast_end <= fcast_date and fcast_end not in end_dates:   # round up errors for M in group_days may cause dups
            end_dates.append(fcast_end)
            cli_list.append(main_key + str(fcast_init.date()) + '+' + str(fcast_end.date()))  # idt+fdt+key_lbl+days+lock_id+<fcast_start>+<fcast_end>
        if len(cli_list) >= periods:
            break
    cli_df = pd.DataFrame(cli_list, columns=['cli_args'], index=range(len(cli_list)))
    cli_df.to_csv(TempUtils.tmpfile(cli_file), index=False)
    s_ut.my_print('all_shards=' + ';'.join(cli_list))


def run_tickets(in_table, fcast_date_str, periods, freq, key_lbl, week_start, cli_file):
    fcast_date = pd.to_datetime(fcast_date_str)

    # "fcast_start"
    fcast_start = pd.to_datetime(fcast_date - pd.to_timedelta(periods, unit=freq))
    fcast_start_str = str(fcast_start.date())
    issue_date = pd.to_datetime(fcast_start - pd.to_timedelta(1, unit=freq))
    issue_date_str = str(issue_date.date())

    qall = 'select count(*) as rows from ' + in_table + ' where key_lbl >= \'' + key_lbl + '\' and ds <= \'' + fcast_date_str + '\' and ds >= \'' + fcast_start_str + '\';'
    s_ut.my_print(qall)
    _cnt_df = ap.presto(qall, use_cache=False)
    if _cnt_df.loc[0, 'rows'] == 0:
        s_ut.my_print('FAILURE no data available for ' + key_lbl + ' ' + fcast_start_str + ' ' + fcast_date_str)
        raise RuntimeError('failure')

    s_ut.my_print('input dates:::::\nweek_start (0 = Monday, 1 = Tuesday, ...): ' + str(week_start) +
                  ' fcast_date: ' + str(fcast_date.date()) +
                  ' fcast_start: ' + str(fcast_start.date()) +
                  ' key_lbl: ' + key_lbl)

    # adjust group fcast days and set the first fcast_start date, eg to first monday after issue date
    cnt = int(freq[:-1]) if len(freq) > 1 else 1
    if 'M' in freq:
        days_per_month = 365.25 / 12.0
        group_days = int(cnt * days_per_month)
        if fcast_start.day == 1:
            first = fcast_start
        else:
            dt_next = issue_date + pd.to_timedelta(1, unit='M')
            first = pd.to_datetime(str(dt_next.year) + '-' + str(dt_next.month) + '-01')
        prev = first - pd.to_timedelta(1, unit='M')
    elif 'W' in freq:
        group_days = cnt * 7
        diff = (week_start - fcast_start.weekday()) % 7
        first = fcast_start + pd.to_timedelta(diff, unit='D')     # first: first fcast_start date with first > issue_date AND first >= fcast_start > sssue_date
        prev = fcast_start + pd.to_timedelta(diff, unit='D') - pd.to_timedelta(14, unit='D')  # start of last complete week that ends on or before issue_date
    elif 'D' in freq:
        group_days = cnt
        first = fcast_start
        prev = first - pd.to_timedelta(1, unit='D')
    else:
        s_ut.my_print('FAILURE multi_agents::invalid freq: ' + str(freq))
        raise RuntimeError('failure')

    if first > fcast_date:
        s_ut.my_print('FAILURE first fcast start incompatible with input dates: : ' + str(first.date()))
        raise RuntimeError('failure')

    days_to_fcast = (fcast_date - prev).days          # to have a full week of actuals and baseline
    n_fcast = np.ceil(days_to_fcast / group_days)   # always the floor which will always include fcast_date. ceil may not
    end_dates = list()
    main_key = issue_date_str + '+' + fcast_date_str + '+' + key_lbl + '+' + str(group_days) + '+'   # + l_id + '+'
    cli_list = []
    for idx in range(1, int(n_fcast) + 5):        # set group of fcast dates that are reported together
        fcast_end, fcast_init, fcast_days = get_values(idx, issue_date, prev, freq, cnt)
        if fcast_init >= issue_date and fcast_end <= fcast_date and fcast_end not in end_dates:   # round up errors for M in group_days may cause dups
            end_dates.append(fcast_end)
            cli_list.append(main_key + str(fcast_init.date()) + '+' + str(fcast_end.date()))  # idt+fdt+key_lbl+days+lock_id+<fcast_start>+<fcast_end>
        if len(cli_list) >= periods:
            break
    cli_df = pd.DataFrame(cli_list, columns=['cli_args'], index=range(len(cli_list)))
    cli_df.to_csv(TempUtils.tmpfile(cli_file), index=False)
    s_ut.my_print('all_shards=' + ';'.join(cli_list))


if __name__ == '__main__':
    run(sys.argv)

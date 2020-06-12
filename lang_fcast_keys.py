"""
python ens_keys.py  <ts_name> <cutoff_date>
ts_name: must be in forecast/config/cfg_data
cutoff_date: list of dates of actuals of the form "[2019-07-27, 2019-08-31, 2019-09-28]" or a single date 2019-09-28
find missing keys for generating fcast cfgs, i.e from last date done to today
"""
import pandas as pd
import sys
import os
import itertools

from capacity_planning.utilities import sys_utils as s_ut


def set_list(arg):  # could use json
    if '[' in arg and ']' in arg:
        vals = arg.replace('[', '').replace(']', '').split(',')
        vals = [d.strip() for d in vals]
    else:
        if '[' not in arg and ']' not in arg:
            vals = [cu_arg]
        else:
            print('invalid date argument: ' + str(arg))
            print('cannot specify ts_name only')
            sys.exit()
    return vals  # a list of args


if __name__ == '__main__':
    print(sys.argv)
    if len(sys.argv) == 3:
        ts_arg, cu_arg = sys.argv[1:]
    elif len(sys.argv) == 2:
        ts_arg = sys.argv[-1]
        cu_arg = None
    else:
        print('must specify both a ts_name and date either in a list, e.g.: \"[2019-07-27, 2019-08-31, 2019-09-28]\" or as a single value, e.g. checkins')
        print('ERROR: invalid sys.argv')
        sys.exit()

    fname = os.path.expanduser('~/my_tmp/cli_keys.csv')
    if os.path.isfile(fname):
        os.remove(fname)

    v_ts = set_list(ts_arg)
    if cu_arg is None:
        data = v_ts
    else:
        v_dates = set_list(cu_arg)
        v_out = list(itertools.product(v_ts, v_dates))
        data = [str(x[0]) + ' ' + str(x[1]) for x in v_out]
    print('cli args: ' + str(data))
    pd.DataFrame({'cli_args': data}).to_csv(fname,  index=False)


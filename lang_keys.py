"""
python lang_keys.py <ts_name> <redo>
ts_name: if there, one of phone-inbound-vol, phone-outbound-vol, phone-inbound-aht, phone-outbound-aht
redo: if there, date to start redo from
find missing keys for generating fcast cfgs, i.e from last date done to today
"""
import pandas as pd
import sys
import os

from capacity_planning.utilities import sys_utils as s_ut

if __name__ == '__main__':
    min_ds = pd.to_datetime('2018-08-01')
    tbl = 'sup.fct_cx_forecast_config'
    print(sys.argv)
    if len(sys.argv) == 1:
        redo = False
        ts_arr = ['phone-inbound-vol', 'phone-outbound-vol', 'phone-inbound-aht', 'phone-outbound-aht']
    elif len(sys.argv) == 2:
        try:
            redo_date = pd.to_datetime(sys.argv[1])
            ts_arr = ['phone-inbound-vol', 'phone-outbound-vol', 'phone-inbound-aht', 'phone-outbound-aht']
            redo = True
        except ValueError:
            ts_arr = [sys.argv[1]]     # 'phone-inbound-vol' # phone-inbound-vol, phone-outbound-vol, phone-inbound-aht, phone-outbound-aht
            redo = False
    elif len(sys.argv) == 3:
        ts, redo_date = sys.argv[1:]
        ts_arr = [ts]
        redo = True
        try:
            redo_date = pd.to_datetime(redo_date)
        except ValueError:
            print('invalid redo date: ' + str(redo_date))
            sys.exit()
    else:
        print('ERROR: invalid sys.argv')
        sys.exit()
    print('ts_arr: ' + str(ts_arr) + ' redo: ' + str(redo))

    # figure out the test dates (may add new ones because we do not know the cutoff argument)
    fname = os.path.expanduser('~/my_tmp/cli_keys.csv')
    if os.path.isfile(fname):
        os.remove(fname)
    today = pd.to_datetime('today').date()
    # if redo is False:   # find pending dates
    #     with s_ut.suppress_stdout_stderr():
    #         import airpy as ap
    #     for ts in ts_arr:
    #         qry = 'select max(ds) as max_ds from ' + tbl + ' where ds <= \'' + str(today) + '\' and ts_name = \'' + ts + '\''
    #         print(qry)
    #         try:
    #             with s_ut.suppress_stdout_stderr():
    #                 z = ap.presto.query(qry, use_cache=False)
    #         except:
    #             with s_ut.suppress_stdout_stderr():
    #                 try:
    #                     z = ap.hive.query(qry, use_cache=False)
    #                 except:
    #                     z = None
    #         if isinstance(z, pd.core.frame.DataFrame) or isinstance(z, pd.core.series.Series):
    #             max_ds = z['max_ds'][0] if len(z) > 0 else None
    #             if max_ds is not None:
    #                 next_ds = pd.to_datetime(max_ds) + pd.DateOffset(months=1)
    #                 print('last partition: ' + str(max_ds) + ' new partition: ' + str(next_ds))
    #             else:
    #                 print('ERROR: no max_ds')
    #                 sys.exit()
    #         else:
    #             print('ERROR: no data returned')
    #             sys.exit()
    # else:  # redo true
    #     next_ds = redo_date

    t_dd = pd.date_range(start=next_ds, end=today, freq='MS')
    data = [ts + ' ' + str(d.date()) for d in t_dd for ts in ts_arr]
    print('fcast cfg keys: ' + str(data))
    pd.DataFrame({'cli_args': data}).to_csv(fname,  index=False)
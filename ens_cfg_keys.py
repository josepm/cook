"""
python ens_keys.py <cutoff_date> <ts_name>
ts_name: one of phone-inbound-vol, phone-outbound-vol, phone-inbound-aht, phone-outbound-aht. If missing default to all
cutoff_date: list of dates of actuals of the form "[2019-07-27, 2019-08-31, 2019-09-28]" or a single date 2019-09-28
find missing keys for generating fcast cfgs, i.e from last date done to today
"""
import pandas as pd
import sys
import os
import itertools

from capacity_planning.utilities import sys_utils as s_ut

if __name__ == '__main__':
    print(sys.argv)
    if len(sys.argv) == 1:
        print('must specify at least dates in a list: \"[2019-07-27, 2019-08-31, 2019-09-28]\" or as a single date: 2019-09-28')
        print('ts_names are optional and default to all')
        sys.exit()
    elif len(sys.argv) == 2:
        ts_arr = ['phone-inbound-vol', 'phone-outbound-vol', 'phone-inbound-aht', 'phone-outbound-aht']
        cu_arg = sys.argv[1]    # 'phone-inbound-vol' # phone-inbound-vol, phone-outbound-vol, phone-inbound-aht, phone-outbound-aht
    elif len(sys.argv) == 3:
        cu_arg, ts = sys.argv[1:]
        ts_arr = [ts]
    else:
        print('ERROR: invalid sys.argv')
        sys.exit()

    if '[' in cu_arg and ']' in cu_arg:
        v_dates = cu_arg.replace('[', '').replace(']', '').split(',')
        v_dates = [d.strip() for d in v_dates]
    else:
        if '[' not in cu_arg and ']' not in cu_arg:
            v_dates = [cu_arg]
        else:
            print('invalid date argument: ' + str(cu_arg))
            print('cannot specify ts_name only')
            sys.exit()

    fname = os.path.expanduser('~/my_tmp/cli_keys.csv')
    if os.path.isfile(fname):
        os.remove(fname)
    v_out = list(itertools.product(v_dates, ts_arr))
    data = [str(x[0]) + ' ' + str(x[1]) for x in v_out]
    print(data)
    pd.DataFrame({'cli_args': data}).to_csv(fname,  index=False)


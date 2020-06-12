import pandas as pd
import sys
import os

from capacity_planning.utilities import sys_utils as s_ut

if __name__ == '__main__':
    print(sys.argv)
    ds = sys.argv[1]
    ts_arr = ['phone-inbound-vol', 'phone-outbound-vol', 'phone-inbound-aht', 'phone-outbound-aht']
    print('ts_arr: ' + str(ts_arr) + ' ds: ' + str(ds))

    # figure out the test dates (may add new ones because we do not know the cutoff argument)
    fname = os.path.expanduser('~/my_tmp/cli_keys.csv')
    if os.path.isfile(fname):
        os.remove(fname)
    data = [ts + ' ' + str(ds) for ts in ts_arr]
    print('fcast cfg keys: ' + str(data))
    pd.DataFrame({'cli_args': data}).to_csv(fname,  index=False)
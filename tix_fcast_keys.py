"""
python tix_fcast_keys.py
ts_name: phone-inbound-vol, phone-outbound-vol, phone-inbound-aht, phone-outbound-aht
"""
import pandas as pd
import sys

if __name__ == '__main__':
    dd = ['2019-07-09', '2019-07-16', '2019-07-23', '2019-07-30', '2019-08-06', '2019-08-13', '2019-08-20',
          '2019-08-27', '2019-09-03', '2019-09-10', '2019-09-17', '2019-09-24', '2019-10-01', '2019-10-08',
          '2019-10-15', '2019-10-22']
    # dd = ['2019-10-15', '2019-10-22', '2019-10-29']
    t_dd = [pd.to_datetime(x) for x in dd]   # check correct
    data = [str(d.date()) for d in t_dd]
    pd.DataFrame({'cli_args': data}).to_csv('~/my_tmp/cli_keys.csv',  index=False)
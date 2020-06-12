#!/Users/josep_ferrandiz/.anaconda/Anaconda3-5.0.0/bin/python
"""
$ python collect.py
load the logs locally and checks termination status. Properly terminated have 'DONE' in the last line.
if OK, load the perf file
"""

import os
import json
import sys


def collect(task):
    # ##############################################################################
    # parameters
    # ##############################################################################
    cfg_file = '/Users/josep_ferrandiz/my_repos/capacity_planning/cook/config/cook_cfg.json'
    with open(cfg_file) as fp:
        d_cfg = json.load(fp)

    ssh_args = d_cfg['ssh_args']
    keys = d_cfg['launch'][task]['keys']
    if keys is None:  # mean launch in a single machine
        keys = [None]
    test = d_cfg['test']

    op_dict = d_cfg['launch'][task]
    repo_name, repo_path, file_lbl, args = op_dict['cmd']

    collect_files = op_dict['collect_files']
    collect_dir = op_dict['collect_dir']

    lx_res_dir = '/efs/home/josep_ferrandiz/'
    mac_res_dir = '/Users/josep_ferrandiz/' + collect_dir

    # ##############################################################################

    print('******************** must run yk before')
    for k in keys:
        print(str(k))
        if k is None:
            _, h = ssh_args[0].split('@')
            v = h.split('.')
            flog = file_lbl + '_' + v[0] + '.log'
        else:
            flog = file_lbl + '_' + k + '.log'
        rmt_f = '~/err/' + flog
        local_f = '/Users/josep_ferrandiz/err/' + flog
        log_cmd = 'scp ' + ssh_args[0] + ':' + rmt_f + ' ' + local_f
        if test is False:
            ret = os.system(log_cmd)
            print('executing: ' + str(log_cmd) + ' return: ' + str(ret))
        else:
            ret = 0
            print('testing:: ' + str(log_cmd))

        if ret == 0:
            with open(local_f) as fptr:
                lines = fptr.readlines()
            if 'DONE' in lines[-1]:
                ok = True
            else:
                print('FAILED::::::::last log line for ' + local_f + ': ' + str(lines[-1]))
                ok = False

            print('log file: ' + local_f + ' is OK: ' + str(ok))
            if ok == True:
                mac_perf_file = mac_res_dir
                for f_in in collect_files:  # tix-D-pull-agent_language:German_2018-05-31_fcast_df.par
                    f = lx_res_dir + collect_dir + k + f_in if k is not None else lx_res_dir + collect_dir + f_in
                    cmd = 'scp' + ' ' + ssh_args[0] + ':' + f + ' ' + mac_perf_file
                    if test is False:
                        fret = os.system(cmd)
                        print('executing: ' + str(cmd) + ' return: ' + str(fret))
                        if fret != 0:
                            print(f + ' failed')
                            sys.exit(0)
                    else:
                        print('testing:: ' + str(cmd))
            else:
                print('WARNING::::::::::::::DONE not found in log file ' + str(local_f))
                # sys.exit(0)
        else:
            print('key: ' + str(k) + ' file: ' + str(rmt_f) + ' log scp error')
    print('this was a test: ' + str(test))
    print('DONE')


if __name__ == '__main__':
    if len(sys.argv) >= 2:
        task = sys.argv[1]
    else:
        print('invalid arguments: ' + str(sys.argv))
        print('ERROR_')
        sys.exit(0)
    collect(task)

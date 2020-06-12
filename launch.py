#!/usr/bin/env python
"""
launch a task on each redspot machine from the desktop
$ python launch.py agents
$ python launch.py fcast

The remote tasks launched are of the form
$ nohup python -u -W ignore <python_file.py> <string_key_arg> <cfg_file.json> > <log_file.log> 2>&1 &

Launch config has a key called launch that contains the cfg of each task:
"launch": {
  <task_name_1> : {
    "rsync": <list of repos to synchronize>
    "cmd": <list of args to build the python file to execute remotely?s>
    "cfg": <name of the common cfg file if the cfg file is common, otherwise null>
    "set_keys": <list of args to build the <string_key_arg> when it is different for each job. Includes python exec and its cfg file>
    "keys": if None, the list of string_key_args is build with set_keys. If True
  },
  <task_name_2: {...}
}
"""

import os
import sys
import subprocess
import stat
import time
import json
import pandas as pd
import getpass
from datetime import datetime
from datetime import timedelta
import platform

sys.path.insert(0, os.path.expanduser('~/my_repos'))

# from capacity_planning.utilities import airflow_task_tracking as att
from capacity_planning.utilities import pandas_utils as p_ut
from capacity_planning.utilities.temp_utils import TempUtils
# from capacity_planning.data import db_funcs as dbf
from capacity_planning.utilities import sys_utils as s_ut


# ##############################################################################
# ##############################################################################


class Launcher:
    WAIT_INTERVAL_SECONDS = 120

    TASKS = (
        ('load', 300),
        ('raw_interactions', 7200),
        ('clean_interactions', 7200),
        ('daily_groups', 7200),
        ('forecast', 7200),
        ('agents', 7200),
        ('tickets', 7200),
        ('phone_inbound', 7200)
    )

    def __init__(self, run_id, d_cfg):
        self.run_id = ''  # run_id
        self.d_cfg = d_cfg
        self.worker_hosts = {}
        self.repo_path = d_cfg.get('repo_path', None)
        self.is_ap = True if platform.system() == 'Darwin' else False  # run with airpy from laptop and on cli from redspot
        if self.repo_path is None:
            s_ut.my_print('ERROR_: repo path is missing')

    def launch_one_task_and_wait_for_completion(self, task, timeout):
        ret = self.run_one_task(task)
        if ret:
            raise RuntimeError("Failed: {task}".format(**locals()))

        end = datetime.now() + timedelta(seconds=timeout)
        if task == 'load':
            return 0
        while datetime.now() < end:
            # success, failure = att.TaskTracker.wait_all_shards_to_complete(self.run_id, self.worker_hosts[task], task)

            # if failure > 0:
            #     s_ut.my_print("Launcher: at least one shard failed in task {task}. Quiting".format(**locals()))
            #     return -1
            # if success == len(self.worker_hosts[task]):
            #     s_ut.my_print("Launcher: all shards succeeded.")
            #     return 0
            s_ut.my_print("Launcher: sleep for {0} seconds".format(Launcher.WAIT_INTERVAL_SECONDS))
            time.sleep(Launcher.WAIT_INTERVAL_SECONDS)
        # timeout
        s_ut.my_print("Launcher: {task} timeout".format(**locals()))
        return -1

    def get_cfg_(self, _cfg_file):
        if _cfg_file is None:
            return None
        else:
            c_file = os.path.expanduser(_cfg_file)
            with open(c_file, 'r') as fp:
                k_cfg = json.load(fp)
            return k_cfg

    def ld_cfg_(self, k_cfg, _cfg_file):
        if _cfg_file is None:
            return None
        else:
            c_file = os.path.expanduser(_cfg_file)
            with open(c_file, 'w') as fp:
                json.dump(fp, k_cfg)

    def run_all(self):
        return self.run_from(Launcher.TASKS[0][0])

    def run_from(self, start_task):
        started = False
        for task_info in Launcher.TASKS:
            task_name = task_info[0]
            timeout = task_info[1]
            if not started and task_name == start_task:
                started = True
            if started:
                if self.launch_one_task_and_wait_for_completion(task_name, timeout) == -1:
                    return -1
        return 0

    def run_one_task(self, task):
        s_ut.my_print("------------ Starting task {task} for run_id {self.run_id} -------------".format(**locals()))
        test = self.d_cfg['test']
        s_ut.my_print('------------ test mode: ' + str(test))

        uname = getpass.getuser()
        rmt_dir = '/efs/home/josep_ferrandiz/'
        op_dict = self.d_cfg['launch'].get(task, None)
        if op_dict is None:
            s_ut.my_print('ERROR_: launch: missing task: ' + str(task))
            return -1

        ssh_args = self.d_cfg['ssh_args']
        workers = len(ssh_args)
        if op_dict['cmd'] is not None:
            repo_name, repo_path, py_file, args = op_dict['cmd']
        else:
            s_ut.my_print('missing cmd for ' + str(task))
            return -1
        set_keys = op_dict.get('set_keys', None)

        # build keys array using set_keys commands
        if set_keys is not None:
            k_repo_name, k_repo_path, k_py_file, k_args = op_dict['set_keys']
            print(op_dict)
            str_args = ' '.join(k_args)
            k_cmd = 'python -u ~/' + self.repo_path + k_repo_name + k_repo_path + k_py_file + '.py ' + str_args
            s_ut.my_print('set_keys cmd: ' + str(k_cmd))
            s_ut.my_print('key args: ' + str(str_args))
            result = subprocess.check_output(k_cmd, shell=True)
            if len(k_args) > 0:
                if 'json' in k_args[0]:
                    with open(os.path.expanduser(k_args[0])) as fp:
                        dcfg = json.load(fp)
                    f_cli = TempUtils.tmpfile(dcfg['cli_file'])
                elif 'csv' in k_args[0]:
                    f_cli = k_args[0]
                else:
                    f_cli = '~/my_tmp/cli_keys.csv'
            else:
                print('invalid k_args')
                sys.exit()

            if not(os.path.exists(os.path.expanduser(f_cli))):
                s_ut.my_print('cli file not created. exiting...')
                sys.exit()
            cli_df = pd.read_csv(f_cli)
            os.remove(os.path.expanduser(f_cli))
            keys = list(cli_df['cli_args'].values)
            s_ut.my_print('number of keys: ' + str(len(keys)))
            host = uname + '@' + ssh_args[0]
            k_drop = list()
            if len(keys) == 0:
                s_ut.my_print('ERROR_: no keys set. exiting')
                return -1
        else:
            keys = op_dict.get('keys', None)
        _cfg_file = op_dict['cfg']

        if task == 'load':  # nothing to run: only rsync code
            rsync = op_dict['rsync']
            user_name = getpass.getuser()
            s_ut.my_print('------------ rsync code for ' + task + ' ---------------')
            cmd1 = 'rsync -r --no-p --no-g --chmod=ugo=rwX --delete --exclude=\".git*\" --exclude=\".idea\" --exclude=\"launch\" --exclude=\"*.pyc\" /Users/' + uname + '/' + self.repo_path
            cmd2 = uname + '@' + ssh_args[0] + ':/efs/home/' + 'josep_ferrandiz' + '/' + self.repo_path
            for repo in rsync:   # load each repo
                r_cmd = cmd1 + repo + '/ ' + cmd2 + repo + '/'
                ret = os.system(r_cmd) if test is False else 0
                s_ut.my_print('rsync::is_test: ' + str(test) + ' cmd: ' + r_cmd + ' ret code: ' + str(ret))
                if ret != 0:
                    s_ut.my_print('ERROR: load for ' + repo + ' failed with code ' + str(ret))
                    sys.exit()
            return 0

        s_ut.my_print('------------ launch ' + task + ' ---------------')
        r_path = '~/' + self.repo_path + repo_name
        cmd = 'nohup python -u -W  ignore ' + r_path + repo_path + py_file + '.py '
        # for a in args:
        #     cmd += str(a) + ' '

        if _cfg_file is not None:
            tail = ' ' + _cfg_file + ' > ~/err/' + py_file + '_'
        else:
            tail = ' > ~/err/' + py_file + '_'
        c2 = '.log 2>&1'

        # set the keys
        sleep_time = 10
        if keys is None:   # set keys to hostname
            n_hosts = op_dict.get('hosts', len(ssh_args))
            keys = [ssh_args[i].split('.')[0] for i in range(n_hosts)]
            commands = [cmd + tail + k + c2 for k in keys]
            print(keys)
        else:
            k_cfg = self.get_cfg_(_cfg_file)
            s_ut.my_print('------------ setting dates ---------------')
            if task in ['clean_interactions', 'raw_interactions', 'daily_groups']:
                init_date, final_date = k_cfg.get('init_date', None), k_cfg.get('final_date', None)
                t_dict = k_cfg.get('tables', None)
                if t_dict is None:
                    s_ut.my_print('ERROR_: missing tables in cfg file')
                    return -1
                in_tables, out_tables = t_dict['input'], t_dict['output']
                for tk, pv in in_tables.items():
                    if '_hive' in tk:
                        in_tables.pop(tk)
                        if '__hive' in tk:
                            in_tables[tk[:-6]] = pv
                        else:
                            in_tables[tk[:-5]] = pv
                final_date = dbf.partition_check(in_tables, final_date, is_ap=self.is_ap)  # final_date_str if acceptable or the largest possible value given the latest partitions
                if final_date is None:
                    s_ut.my_print('ERROR_: final_date incompatible with latest partitions')
                    return -1
                else:
                    s_ut.my_print(task + ' has final date: ' + str(final_date))
                init_date = max(init_date, self.d_cfg['earliest_date']) if init_date is not None else init_date
                init_date = dbf.partition_check(out_tables, init_date, is_ap=self.is_ap)

                if init_date is None:
                    s_ut.my_print('ERROR_: init_date incompatible with latest partitions')
                    return -1
                else:
                    s_ut.my_print(task + ' has init date: ' + str(init_date))

                ds_date = str((pd.datetime.now() - pd.to_timedelta(4, unit='D')).date())  # date for dim tables
                w_days = k_cfg.get('w_days', None)
                if w_days is None:
                    s_ut.my_print('ERROR_: w_days must be specified')
                    return -1

                ttl_days = (pd.to_datetime(final_date) - pd.to_datetime(init_date)).days
                if ttl_days <= 0:
                    s_ut.my_print('No work to do: ttl_days: ' + str(ttl_days))
                    return -1

                # adjust start date to have blocks of w_days
                blocks = ttl_days // w_days if ttl_days % w_days == 0 else 1 + ttl_days // w_days
                start_date = pd.to_datetime(final_date) - pd.to_timedelta(w_days * blocks, unit='D')  # blocks of w_days
                end_date = pd.to_datetime(final_date)
                dates = p_ut.set_date_range(start_date, end_date, str(w_days) + 'D')

                if len(dates) == 0:
                    s_ut.my_print('nothing to do:: final date: ' + str(final_date) + ' init_data: ' + str(init_date))
                    sys.exit(0)
                keys = [str(x[0].date()) + '_' + str(x[1].date()) + '_' + ds_date for x in dates]
                if start_date > end_date:
                    s_ut.my_print('ERROR: invalid date ranges for ' + task + ' start_date: ' + str(start_date.date()) + ' end_date: ' + str(end_date.date()))
                    sys.exit()

                s_ut.my_print('******* task summary: ' + task + '\ninit_date: ' + str(start_date.date()) +
                              ' final_date: ' + final_date +
                              ' w_days: ' + str(w_days) +
                              ' number of jobs: ' + str(len(keys)))
                s_ut.my_print('command line strings: ' + str(keys))

            elif task in ['forecast', 'crossval']:
                fcast_periods, time_scale = k_cfg.get('fcast_periods', None), k_cfg.get('time_scale', None)
                issue_date, fcast_date = k_cfg.get('issue_date', None), k_cfg.get('fcast_date', None)
                in_table, out_table = list(k_cfg['tables']['input'].keys())[0], list(k_cfg['tables']['output'].keys())[0]
                cfg_key_lbl_ = k_cfg['key_lbl']
                ts_str = '+'.join(keys['ts_names'])
                last_p = dbf.partition_check({in_table: 'ds'}, None, is_ap=self.is_ap, where=' where key_lbl = \'' + cfg_key_lbl_ + '\';')
                s_ut.my_print('task: forecast last input partition: ' + str(last_p))
                if last_p is None or last_p == -1:
                    s_ut.my_print('ERROR_: no group data available for issue date')
                    return -1
                if issue_date is None:
                    issue_date = last_p
                keys_ = list()
                if issue_date > last_p:
                    s_ut.my_print('ERROR_: no data available for issue date: ' + issue_date)
                    return -1
                fcast_date = str((pd.to_datetime(issue_date) + pd.to_timedelta(fcast_periods, unit=time_scale)).date())
                keys_.append(issue_date + '_' + fcast_date + '_' + ts_str)
                if k_cfg.get('run_id', None) is not None:
                    self.run_id = k_cfg['run_id']
                    s_ut.my_print('WARNING: resetting run_id to ' + self.run_id)
                keys = keys_ * (len(ssh_args))  # all hosts will run the same but will be managed by lock file across hosts
                s_ut.my_print('******* task summary: ' + task + '\nnumber of fcasts: ' + str(len(keys)))
                sleep_time = 30
            else:
                pass

            # final cmd: python foo.py run_id key_i args cfg_file > log_file.log 2>&1 &
            if isinstance(keys, (list, str, tuple)):
                s_args = ' '.join([str(a) for a in args])
                join_keys = ['+'.join(k.split(' ')) for k in keys]
                commands = [cmd + self.run_id + ' ' + keys[i] + ' ' + s_args + tail + join_keys[i] + c2 for i in range(len(keys))]
                # commands = [cmd + self.run_id + ' ' + keys[i] + tail + str(i) + c2 for i in range(len(keys))]
            else:
                commands = cmd + keys + tail + keys + c2

        # generate script file names
        script_files = list()
        for i in range(len(ssh_args)):  # round robin on hosts. Make sure CPUs are set to share hosts among several concurrent launches
            s_file = TempUtils.tmpfile(ssh_args[i] + '_' + task + '_' + str(i) + '_script.sh')
            script_files.append(s_file)
            s_ut.my_print('creating file ' + s_file)
            with open(s_file, 'w') as fptr:
                fptr.write('#!/bin/bash\nsource /efs/home/josep_ferrandiz/.bashrc\n')
                if i == 0:
                    fptr.write('/bin/rm -rf /efs/home/josep_ferrandiz/my_repos/capacity_planning/*/__pycache__/*\n')

        # load the remote tasks
        self.worker_hosts[task] = []
        pending = None
        for i in range(len(commands)):  # round robin on hosts. Make sure CPUs are set to share hosts among several concurrent launches
            if pending is None or i in pending:
                h_idx = i % len(ssh_args)   # host index
                cmd = commands[i]
                vcmd = cmd.split('/')
                host = ssh_args[h_idx]
                host_name = str(host.split('.')[0])
                vcmd[-1] = host_name + '+' + vcmd[-1]
                self.worker_hosts[task].append(host)
                s_ut.my_print(str(i) + ' host: ' + host_name + ' command: ' + cmd)
                script = script_files[h_idx]
                with open(script, 'a') as fptr:
                    fptr.write(cmd + '\n')

        for h_idx in range(len(ssh_args)):  # round robin on hosts. Make sure CPUs are set to share hosts among several concurrent launches
            script = script_files[h_idx]
            s_ut.my_print('is_test: ' + str(test) + ' ssh_cmd:  ssh -T ' + uname + '@' + ssh_args[h_idx] + ' < cat ' + script)
            if test is False:
                time.sleep(sleep_time)
                os.chmod(script, stat.S_IRWXU)
                cat = subprocess.Popen(['cat', script], stdout=subprocess.PIPE)
                ssh = subprocess.Popen(['ssh', '-T', uname + '@' + ssh_args[h_idx]], stdin=cat.stdout, stdout=subprocess.PIPE)
                end_of_pipe = ssh.stdout
                print('ret:::::' + str(ssh.returncode) + ' ' + str(cat.returncode))
                time.sleep(10)

        s_ut.my_print("------------------------- Launched remote tasks ---------------------------")
        return 0


if __name__ == '__main__':
    if len(sys.argv) == 2:
        if sys.argv[1] != 'all':
            _task = sys.argv[1]
        _run_id = 100   # att.TaskTracker.gen_run_id()
    elif len(sys.argv) == 4 and sys.argv[1] == 'resume':
        _task = sys.argv[2]
        _run_id = sys.argv[3]
    else:
        s_ut.my_print('invalid arguments: ' + str(sys.argv))
        s_ut.my_print('ERROR_')
        sys.exit(-1)
    cfg_file = os.path.expanduser('~/my_repos/capacity_planning/cook/config/cook_cfg.json')
    with open(cfg_file) as fp:
        _d_cfg = json.load(fp)
    launcher = Launcher(_run_id, _d_cfg)
    test = _d_cfg['test']
    if sys.argv[1] == 'all':
        ret = launcher.run_all()
    elif sys.argv[1] == 'resume':
        ret = launcher.run_from(_task)
    else:
        ret = launcher.run_one_task(_task)

    if ret == 0:
        if test is False:
            s_ut.my_print('LAUNCH COMPLETE: ' + _task)
        else:
            s_ut.my_print('TEST COMPLETE')


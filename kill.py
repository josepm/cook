"""
$ python kill.py
kill an erroneous launch
"""

import os
import sys
import subprocess
import stat
import json
import time
import getpass

sys.path.insert(0, os.path.expanduser('~/my_repos'))

from capacity_planning.utilities.temp_utils import TempUtils

# ##############################################################################
# parameters
# ##############################################################################
# cfg_file = '/Users/josep_ferrandiz/my_repos/capacity_planning/cook/config/cook_cfg.json'
cfg_file = os.path.dirname(os.path.abspath(__file__)) + '/config/cook_cfg.json'
with open(cfg_file) as fp:
    d_cfg = json.load(fp)

ssh_args = d_cfg['ssh_args']
repo_name, repo_path, py_file, args = d_cfg['launch']['kill']['cmd']
uname = getpass.getuser()


# ##############################################################################
# ##############################################################################

print('&&&&&&&&&&&&&&&&& must run yk before &&&&&&&&&&&&&&&&&')
print('------------------------- pkill ----------------------')


cmd = 'nohup python -u ~/my_repos/capacity_planning/' + repo_name + repo_path + py_file + '.py  '
err = ' > ~/err/' + py_file + '_'
c2 = '.log 2>&1 &'
command = cmd + err + c2
print(command)

script = TempUtils.tmpfile('script.sh')
for h in ssh_args:
    host = uname + '@' + h
    command = cmd + err + h + c2
    print('host: ' + str(host) + ' cmd: ' + command)
    with open(script, 'w') as fptr:
        fptr.write(command)
    os.chmod(script, stat.S_IRWXU)
    cat = subprocess.Popen(['cat', script], stdout=subprocess.PIPE)
    ssh = subprocess.Popen(['ssh', '-T', h], stdin=cat.stdout, stdout=subprocess.PIPE)
    end_of_pipe = ssh.stdout
    time.sleep(2)


print('DONE')


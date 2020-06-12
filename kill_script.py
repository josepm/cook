"""
kill my processes
"""
import psutil
from socket import gethostname
import os
import sys
import getpass


def get_children(pid):
    current_process = psutil.Process(pid)
    children = current_process.children(recursive=True)
    return [child.pid for child in children]


if __name__ == '__main__':
    print(sys.argv)
    if len(sys.argv) == 2:
        ppid = sys.argv[1]
    else:
        ppid = None
    pid = os.getpid()
    print('kill script starts in ' + str(gethostname()) + ' with this pid: ' + str(pid) + ' and ppid: ' + str(ppid))
    xtr = 0
    uname = getpass.getuser()
    for proc in psutil.process_iter():
        if uname in proc.username():
            if pid != proc.pid and ('python' in proc.name() or 'bash' in proc.name()):
                xtr += 1
                print('process: ' + str(proc.pid) + ' name: ' + str(proc.name()) + ' user: ' + str(proc.username()) + ' ctr: ' + str(xtr))
                if proc.ppid() == ppid or ppid is None:
                    print('\tkilling process: ' + str(proc.pid) + ' name: ' + str(proc.name()) + ' user: ' + str(proc.username()))
                    try:
                        proc.kill()
                    except:
                        print('\t****************************** could not kill process: ' + str(proc.pid))

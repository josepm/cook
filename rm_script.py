"""
$ python rm_script days path file_pat
rm files older that days in path
if file_pat = * or missing remove all
file_path cannot be a number
"""
import os
import sys
import time


if __name__ == '__main__':
    print('$$$$$$$$$$$$$ remove files script $$$$$$$$$$$$')
    args = sys.argv[1:]
    arg_groups = list()
    print('rm args: ' + str(arg_groups))
    new_args = None
    for a in args:
        try:
            a = int(a)
            if new_args is not None:
                arg_groups.append(new_args)
            new_args = [a]
        except ValueError:
            new_args.append(a)
    if new_args is not None:
        arg_groups.append(new_args)

    for g in arg_groups:
        if len(g) == 2:
            days, path = g
            file_pat = None
        elif len(g) == 3:
            days, path, file_pat = g
            if file_pat == '*' or file_pat == 'None':
                file_pat = None
        else:
            print('invalid arguments: ' + str(arg_groups) + ' args: ' + str(sys.argv[1:]))
            sys.exit(0)
        print('removing: days: ' + str(days) + ' path: ' + str(path) + ' pattern: ' + str(file_pat))

        fpath = os.path.expanduser(path)
        now = time.time()
        ctr = 0
        if os.path.isdir(fpath):
            for f in os.listdir(fpath):
                if file_pat is not None:
                    if file_pat not in f:
                        continue
                file_path = os.path.join(fpath, f)
                if os.stat(file_path).st_mtime < now - int(days) * 86400:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(file_path + ' removed')
                        ctr += 1
            print(fpath + ': files removed: ' + str(ctr))
        else:
            print('directory ' + fpath + ' does not exist')

"""
upgrade anaconda
run anaconda shell script and deploy in ~/.anaconda/<new_anaconda>
"""
import os
p_file = '~/pkg_cur.txt'        # current packages file from pip freeze > pkt_cur.txt
n_file = '~/pkg_new.txt'        # default packages in the new anaconda distro
new_pip = '~/.anaconda/Anaconda3-5.3.0/bin/pip'

with open(os.path.expanduser(p_file)) as fp:
    pkg = fp.readlines()
p_pkg = [z.split('==')[0] for z in pkg]  # current packages
with open(os.path.expanduser(n_file)) as fp:
    pkg = fp.readlines()
n_pkg = [z.split('==')[0] for z in pkg]  # default packages

to_add = list(set(p_pkg) - set(n_pkg))   # packages to add

# special adds
os.system('conda install gcc')
os.system('pip install pystan')
os.system('conda install -c conda-forge fbprophet')
os.system('conda install -c conda-forge lapack')
os.system('conda install -c cvxgrp cvxpy ecos')
os.system('conda install -c conda-forge tslearn')
os.system('conda install libgcc')

for p in to_add:
    print('********* package: ' + p)
    cmd = os.path.expanduser(new_pip) + ' install ' + p
    os.system(cmd)

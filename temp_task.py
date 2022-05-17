import json
import os
import tarfile
from subprocess import Popen
from subprocess import run
from uuid import uuid4

from pickler import load_state


def run_server_manager_client_task():
    try:
        if os.path.isfile('server-manager-client-installed'):
            print('server-manager-client-installed task is already done')
            return
        state = load_state('~/vmware-manager-state')
        server_name = str(uuid4()) if state is None else state['server_name']
        my_dir = 'c:\\server-manager-client'
        with tarfile.open('server-manager-client.tar.bz2', 'r:bz2') as fp:
            fp.extractall(my_dir)
        run(['python', '-m', 'venv', 'venv'], timeout=300, cwd=my_dir)
        with open(os.path.join(my_dir, 'venv', 'config.json'), 'w') as fp:
            json.dump({'alias': server_name}, fp)
        run(['venv\\Scripts\\python', '-m', 'pip', 'install',
            '-r', 'requirements.txt'], timeout=300, cwd=my_dir, shell=True)
        Popen(['venv\\Scripts\\python', 'run_production.py'], cwd=my_dir, shell=True)
        with open('server-manager-client-installed', 'w') as fp:
            pass
    except Exception as exp:
        print(f'Exception in run_server_manager_client_task: {exp}')


if __name__ == '__main__':
    run_server_manager_client_task()

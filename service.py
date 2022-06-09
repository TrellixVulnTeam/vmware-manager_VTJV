import io
import os
import urllib.request
import zipfile
from subprocess import DEVNULL
from subprocess import run

nssm_path = 'c:\\nssm-2.24\\win64\\nssm.exe'


def download_nssm():
    try:
        if os.path.exists(nssm_path):
            return True
        print('Downloading nssm...')
        res = urllib.request.urlopen('https://nssm.cc/release/nssm-2.24.zip', timeout=30)
        bytes = io.BytesIO(res.read())
        my_file = zipfile.ZipFile(bytes)
        my_file.extractall('c:\\')
        return True
    except Exception:
        return False


def set_smc_service(start=True):
    try:
        if os.path.isfile('task1'):
            print('task1 is already done')
            return
        if not download_nssm():
            return
        run([nssm_path, 'stop', 'SMCService'])
        run([nssm_path, 'remove', 'SMCService', 'confirm'])
        base_dir = 'c:\\server-manager-client'
        python_path = os.path.join(base_dir, 'venv', 'Scripts', 'python.exe')
        script_path = os.path.join('run_production.py')
        run([nssm_path, 'install', 'SMCService', python_path, script_path],
            stdout=DEVNULL, stderr=DEVNULL)
        run([nssm_path, 'set', 'SMCService', 'AppDirectory', base_dir],
            stdout=DEVNULL, stderr=DEVNULL)
        if start:
            run([nssm_path, 'start', 'SMCService'], stdout=DEVNULL, stderr=DEVNULL)
        with open('task1', 'w'):
            pass
    except Exception:
        pass


def remove_smc_service():
    try:
        if not download_nssm():
            return
        run([nssm_path, 'stop', 'SMCService'])
        run([nssm_path, 'remove', 'SMCService', 'confirm'])
    except Exception:
        pass

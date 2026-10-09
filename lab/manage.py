import argparse
import json
import os
from pathlib import Path
import plistlib
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import psutil
from .common import DATA,ROOT

LABEL='local.anywear.consumer-lab'

def login_target():
    return Path.home()/'Library/LaunchAgents'/f'{LABEL}.plist'

def process():
    try:
        saved=json.loads((DATA/'supervisor.json').read_text()); proc=psutil.Process(saved['pid'])
        if abs(proc.create_time()-saved['started'])<.01 and 'lab.supervisor' in ' '.join(proc.cmdline()): return proc
    except (OSError,ValueError,psutil.Error): pass
    return None

def status():
    p=process(); result={'running':bool(p),'pid':p.pid if p else None,'web':'http://127.0.0.1:3001/lab/','data':str(DATA)}
    try:
        with urllib.request.urlopen('http://127.0.0.1:8001/api/lab/health',timeout=4) as r: result['health']=json.load(r)
    except Exception: result['health']=None
    print(json.dumps(result,ensure_ascii=False,indent=2)); return result

def start():
    if process(): return status()
    node=os.environ.get('ANYWEAR_NODE') or shutil.which('node')
    if not node: raise SystemExit('Node is required')
    # Refuse to take over other services.
    import socket
    for port in (3001,8001):
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            try: sock.bind(('127.0.0.1',port))
            except OSError: raise SystemExit(f'Port {port} is occupied; existing service left running.')
    subprocess.run([node,str(ROOT/'node_modules/vite/bin/vite.js'),'build'],cwd=ROOT,check=True)
    DATA.mkdir(parents=True,exist_ok=True)
    if sys.platform=='darwin' and login_target().exists():
        subprocess.run(['launchctl','bootstrap',f'gui/{os.getuid()}',str(login_target())],check=True)
    else:
        with (DATA/'supervisor.log').open('ab',buffering=0) as log:
            subprocess.Popen([sys.executable,'-m','lab.supervisor'],cwd=ROOT,env={**os.environ,'ANYWEAR_NODE':node,'ANYWEAR_CODEX':os.environ.get('ANYWEAR_CODEX') or shutil.which('codex') or ''},
                             stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    for _ in range(40):
        if process():
            try:
                with urllib.request.urlopen('http://127.0.0.1:3001/lab/',timeout=1) as r:
                    if r.status==200: break
            except Exception: pass
        time.sleep(.25)
    return status()

def stop():
    p=process()
    if sys.platform=='darwin' and login_target().exists():
        subprocess.run(['launchctl','bootout',f'gui/{os.getuid()}',str(login_target())],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        p=process()
    if p:
        try: p.send_signal(signal.SIGTERM)
        except psutil.NoSuchProcess: p=None
    if p:
        deadline=time.monotonic()+15
        while p.is_running():
            try:
                if p.status()==psutil.STATUS_ZOMBIE: break
            except psutil.NoSuchProcess: break
            if time.monotonic()>deadline: raise SystemExit('Still shutting down; inspect status before retrying.')
            time.sleep(.1)
    print('Stopped / 已停止。 Persisted experiments are retained.')

def login_service(remove=False):
    if sys.platform!='darwin': raise SystemExit('Login service is supported on macOS; see README for other hosts.')
    target=login_target(); domain=f'gui/{os.getuid()}'
    if target.exists(): subprocess.run(['launchctl','bootout',domain,str(target)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if remove:
        target.unlink(missing_ok=True); print('Login service removed.'); return
    stop(); target.parent.mkdir(parents=True,exist_ok=True)
    node=os.environ.get('ANYWEAR_NODE') or shutil.which('node')
    config={'Label':LABEL,'ProgramArguments':[sys.executable,'-m','lab.supervisor'],'WorkingDirectory':str(ROOT),
      'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':10,
      'EnvironmentVariables':{'ANYWEAR_NODE':node,'PATH':os.environ.get('PATH','/usr/bin:/bin'),'ANYWEAR_LAB_DATA':str(DATA),'ANYWEAR_CODEX':os.environ.get('ANYWEAR_CODEX') or shutil.which('codex') or ''},
      'StandardOutPath':str(DATA/'launchd.log'),'StandardErrorPath':str(DATA/'launchd.log')}
    DATA.mkdir(parents=True,exist_ok=True); target.write_bytes(plistlib.dumps(config))
    subprocess.run(['launchctl','bootstrap',domain,str(target)],check=True)
    print(f'Installed login service: {target}')

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=['start','stop','restart','status','install-login','uninstall-login'])
    command=parser.parse_args().command
    if command=='start': start()
    elif command=='stop': stop()
    elif command=='restart': stop(); start()
    elif command=='status': status()
    else: login_service(command=='uninstall-login')

if __name__=='__main__': main()

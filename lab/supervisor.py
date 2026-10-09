"""Local process supervisor. Does not advance simulation time itself."""
import fcntl
import os
import signal
import subprocess
import sys
import threading
import time
import psutil
from .common import DATA, ROOT, canonical
from .store import Store

def main():
    DATA.mkdir(parents=True,exist_ok=True)
    lock=(DATA/'supervisor.lock').open('w')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: raise SystemExit('Supervisor already running')
    (DATA/'supervisor.json').write_text(canonical({'pid':os.getpid(),'started':psutil.Process().create_time()}))
    stop=threading.Event()
    for sig in (signal.SIGINT,signal.SIGTERM): signal.signal(sig,lambda *_:stop.set())
    node=os.environ.get('ANYWEAR_NODE')
    if not node: raise SystemExit('ANYWEAR_NODE required; use pnpm lab:start')
    commands={'api':[sys.executable,'-m','uvicorn','lab.api:app','--host','127.0.0.1','--port','8001','--no-access-log','--timeout-graceful-shutdown','5'],
              'worker':[sys.executable,'-m','lab.worker'],'web':[node,'server.mjs']}
    env={**os.environ,'PORT':'3001','HOST':'127.0.0.1','ANYWEAR_LAB_API_PORT':'8001','ANYWEAR_LAB_WEB_PORT':'3001'}
    children={}; logs={}; store=Store(); heartbeat=0
    try:
        while not stop.is_set():
            for name,command in commands.items():
                if name not in children or children[name].poll() is not None:
                    if name not in logs: logs[name]=(DATA/f'{name}-service.log').open('ab',buffering=0)
                    children[name]=subprocess.Popen(command,cwd=ROOT,env=env,stdout=logs[name],stderr=logs[name],start_new_session=True)
            if time.time()-heartbeat>5:
                store.heartbeat('supervisor',{'pid':os.getpid(),'children':{k:v.pid for k,v in children.items()}})
                store.heartbeat('web',{'pid':children['web'].pid,'alive':children['web'].poll() is None})
                heartbeat=time.time()
            stop.wait(1)
    finally:
        for proc in children.values():
            try: os.killpg(proc.pid,signal.SIGTERM)
            except ProcessLookupError: pass
        deadline=time.monotonic()+10
        for proc in children.values():
            try: proc.wait(timeout=max(.1,deadline-time.monotonic()))
            except subprocess.TimeoutExpired:
                try: os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError: pass
        for log in logs.values(): log.close()
        store.heartbeat('supervisor',{'pid':os.getpid(),'stopped':True})
        (DATA/'supervisor.json').unlink(missing_ok=True); lock.close()

if __name__=='__main__': main()

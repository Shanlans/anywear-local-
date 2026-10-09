from __future__ import annotations
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import signal
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import psutil
from .agents import decide,resolve_decision
from .common import DATA, ROOT, canonical, digest
from .engine import Engine,demo_decision
from .model import CodexModel,ModelFailure
from .store import Store,Conflict
from .doctor import gate_valid

STOP=threading.Event()

def code_fingerprint():
    return digest({str(p.relative_to(ROOT)):digest(p.read_text()) for p in sorted((ROOT/'lab').glob('*.py'))})

LOADED_CODE=code_fingerprint()

def execute(store,job,attempt,config):
    model=None
    try:
        if config['mode']=='demo':
            response=demo_decision(job['observation'])
            metadata={'mode':'demo','cli_usage':None,'sample_text_calls':0}
        else:
            def spawned(pid): store.spawned(attempt,pid,psutil.Process(pid).create_time())
            model=CodexModel(config['model'],config['timeout_seconds'],cancel=STOP.is_set,on_spawn=spawned)
            response,component=decide(job['observation'],job['memory'],model)
            metadata={**model.metadata,**component,'mode':'codex'}
            if metadata.get('tools_forwarded')!=0 or metadata.get('input_messages_forwarded')!=1:
                raise ModelFailure('ISOLATION_FAILED')
        resolve_decision(response,job['observation']['allowed_actions'])
        store.respond(job['id'],attempt,job['fence'],response,metadata)
    except Conflict:
        logging.warning('LATE_WORKER_RESULT job=%s',job['id'])
    except Exception as error:
        code=error.code if isinstance(error,ModelFailure) else ('INVALID_RESPONSE' if isinstance(error,ValueError) else 'WORKER_ERROR')
        unknown=error.unknown if isinstance(error,ModelFailure) else False
        metadata={**(model.metadata if model else {}),'mode':config['mode'],'error_code':code}
        try: store.respond(job['id'],attempt,job['fence'],None,metadata,code,unknown)
        except Conflict: logging.warning('STALE_FAILURE job=%s',job['id'])

def drive(store,run):
    row=store.get(run); engine=Engine(row['state']); before=engine.hash()
    jobs=store.jobs(run, before)
    if row['status'] in ('PAUSING','STOPPING'):
        if not any(j['status']=='spawned' for j in jobs):
            store.save(run,engine,before,row['fence'],status='PAUSED' if row['status']=='PAUSING' else 'STOPPED')
        return
    if row['status']!='RUNNING': return
    if row['config']['mode']=='codex' and row['manifest']['source_fingerprint']!=LOADED_CODE:
        with store.tx() as db: db.execute("UPDATE runs SET status='PAUSED',error='SOURCE_VERSION_MISMATCH' WHERE id=?",(run,))
        return
    if engine.complete():
        status='COMPLETED' if all(a['status']!='CENSORED' for w in engine.s['worlds'].values() for a in w['agents'].values()) else 'INCOMPLETE'
        store.save(run,engine,before,row['fence'],status=status); return
    if engine.ready():
        jobs=store.prepare_jobs(run,engine,row['fence'])
        if all(j['status']=='responded' for j in jobs):
            by_agent={(j['world'],j['agent']):j for j in jobs}
            engine.events=[]
            for world,aid in engine.ready():
                job=by_agent[(world,aid)]
                response=resolve_decision(job['response'],job['observation']['allowed_actions'])
                engine.apply(world,aid,response,job['observation']['allowed_actions'])
            breaks=set(row['controls'].get('breakpoints',[]))
            hit=any(e['kind'] in breaks for e in engine.events)
            status='PAUSED' if row['step'] or hit else None
            store.save(run,engine,before,row['fence'],[j['id'] for j in jobs],status=status)
        return
    breaks=set(row['controls'].get('breakpoints',[]))
    engine.advance(one_event=row['step']=='step_event',breakpoints=breaks)
    hit=any(e['kind'] in breaks for e in engine.events)
    store.save(run,engine,before,row['fence'],status='PAUSED' if row['step']=='step_event' or hit else None)

def recover_processes(store):
    with store.connect() as db:
        rows=db.execute("SELECT pid,process_start FROM attempts WHERE status IN ('spawned','reserved') AND pid IS NOT NULL").fetchall()
    for row in rows:
        try:
            proc=psutil.Process(row['pid'])
            if abs(proc.create_time()-row['process_start'])<.01 and 'codex' in proc.name().lower():
                os.killpg(proc.pid,signal.SIGTERM)
        except (psutil.Error,ProcessLookupError,PermissionError): pass
    store.new_fence()

def main():
    DATA.mkdir(parents=True,exist_ok=True)
    lock=(DATA/'worker.lock').open('w')
    try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: raise SystemExit('Worker already active')
    handler=RotatingFileHandler(DATA/'worker.log',maxBytes=2_000_000,backupCount=5)
    logging.basicConfig(level=logging.INFO,handlers=[handler],format='%(asctime)s %(levelname)s %(message)s')
    for sig in (signal.SIGINT,signal.SIGTERM): signal.signal(sig,lambda *_:STOP.set())
    store=Store(); recover_processes(store)
    pool=ThreadPoolExecutor(max_workers=2); futures={}; heartbeat=0
    try:
        while not STOP.is_set():
            now=time.time()
            if now-heartbeat>=5:
                store.heartbeat('worker',{'pid':os.getpid(),'active':len(futures),
                    'rss_bytes':psutil.Process().memory_info().rss,'free_disk_bytes':psutil.disk_usage(DATA).free})
                heartbeat=now
                alarm=('SOURCE_CHANGED' if code_fingerprint()!=LOADED_CODE else ('LOW_DISK' if psutil.disk_usage(DATA).free<500_000_000 else None))
                if alarm:
                    with store.tx() as db: db.execute("UPDATE runs SET status='PAUSING',error=? WHERE status='RUNNING'",(alarm,))
            for key,future in list(futures.items()):
                if future.done():
                    try: future.result()
                    except Exception: logging.error('FUTURE_FAILED job=%s',key)
                    del futures[key]
            rows=store.list()
            for row in reversed(rows):
                if row['status'] not in ('RUNNING','PAUSING','STOPPING'): continue
                try:
                    drive(store,row['id'])
                    if len(futures)<2:
                        current=store.get(row['id'])
                        if current['status']!='RUNNING': continue
                        for job in store.jobs(row['id'],current['state_hash']):
                            if len(futures)>=2: break
                            if job['status']=='queued' and job['id'] not in futures:
                                if current['config']['mode']=='codex':
                                    if not gate_valid():
                                        store.control(row['id'],'pause');
                                        with store.tx() as db: db.execute("UPDATE runs SET error='ISOLATION_GATE_REQUIRED' WHERE id=?",(row['id'],))
                                        break
                                attempt=store.claim(job['id'],job['fence'])
                                if attempt: futures[job['id']]=pool.submit(execute,store,job,attempt,current['config'])
                except Exception as error:
                    logging.error('DRIVE_FAILED run=%s type=%s',row['id'],type(error).__name__)
                    with store.tx() as db:
                        db.execute("UPDATE runs SET status='PAUSED',error='ENGINE_INTEGRITY' WHERE id=?",(row['id'],))
            STOP.wait(.08)
    finally:
        STOP.set(); pool.shutdown(wait=True,cancel_futures=True)
        store.heartbeat('worker',{'pid':os.getpid(),'stopped':True}); lock.close()

if __name__=='__main__': main()

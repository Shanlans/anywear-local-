from __future__ import annotations
import contextlib
import copy
import json
import sqlite3
import subprocess
import sys
import importlib.metadata
import time
import uuid
from pathlib import Path
from .common import DATA, ROOT, RunConfig, canonical, digest
from .engine import Engine

class Conflict(Exception): pass

class Store:
    def __init__(self,path=None):
        self.path=Path(path or DATA/'lab.sqlite3'); self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS runs(
              id TEXT PRIMARY KEY, config TEXT NOT NULL, initial TEXT NOT NULL, state TEXT NOT NULL,
              state_hash TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL,
              parent TEXT, parent_seq INTEGER, error TEXT, step TEXT, budget INTEGER NOT NULL,
              fence INTEGER NOT NULL DEFAULT 0, manifest TEXT NOT NULL DEFAULT '{}', controls TEXT NOT NULL DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS events(
              run TEXT NOT NULL, seq INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY(run,seq));
            CREATE TABLE IF NOT EXISTS jobs(
              id TEXT PRIMARY KEY, run TEXT NOT NULL, frontier TEXT NOT NULL, world TEXT NOT NULL,
              agent TEXT NOT NULL, observation TEXT NOT NULL, memory TEXT NOT NULL,
              status TEXT NOT NULL, response TEXT, metadata TEXT, error TEXT, fence INTEGER NOT NULL,
              lease_until REAL, retries INTEGER NOT NULL DEFAULT 0);
            CREATE INDEX IF NOT EXISTS jobs_run ON jobs(run,status);
            CREATE TABLE IF NOT EXISTS attempts(
              id TEXT PRIMARY KEY, job TEXT NOT NULL, run TEXT NOT NULL, status TEXT NOT NULL,
              started REAL NOT NULL, ended REAL, metadata TEXT, pid INTEGER, process_start REAL);
            CREATE TABLE IF NOT EXISTS checkpoints(
              run TEXT NOT NULL, seq INTEGER NOT NULL, state TEXT NOT NULL, hash TEXT NOT NULL,
              PRIMARY KEY(run,seq));
            CREATE TABLE IF NOT EXISTS analyses(
              id TEXT PRIMARY KEY, run TEXT NOT NULL, settings TEXT NOT NULL, created REAL NOT NULL,
              post_hoc INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS issues(
              id TEXT PRIMARY KEY, run TEXT, seq INTEGER, code TEXT, severity TEXT,
              status TEXT, detail TEXT, created REAL, fix_commit TEXT);
            CREATE TABLE IF NOT EXISTS health(
              key TEXT PRIMARY KEY, value TEXT NOT NULL, updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS batches(
              id TEXT PRIMARY KEY, kind TEXT NOT NULL, config TEXT NOT NULL, cells TEXT NOT NULL,
              created REAL NOT NULL);
            ''')
    def connect(self):
        db=sqlite3.connect(self.path,timeout=30,isolation_level=None)
        db.row_factory=sqlite3.Row; db.execute('PRAGMA busy_timeout=30000'); db.execute('PRAGMA foreign_keys=ON')
        return db
    @contextlib.contextmanager
    def tx(self):
        db=self.connect()
        try:
            db.execute('BEGIN IMMEDIATE'); yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()
    def create(self,config,parent=None,state=None,db=None):
        c=RunConfig.model_validate(config).model_dump()
        engine=Engine(copy.deepcopy(state)) if state else Engine.create(c)
        if state: engine.s['config']=c
        engine.invariants(); run='run-'+uuid.uuid4().hex[:12]; now=time.time()
        try:
            commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
            dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip())
        except Exception: commit=None; dirty=None
        source_hashes={str(p.relative_to(ROOT)):digest(p.read_text()) for p in sorted((ROOT/'lab').glob('*.py'))}
        manifest={'schema_version':1,'git_commit':commit,'dirty':dirty,'source_hashes':source_hashes,
            'protocol_hash':digest((ROOT/'docs/GAME_PLAN.md').read_text()),
            'python':sys.version.split()[0],'concordia':importlib.metadata.version('gdm-concordia'),
            'config_hash':digest(c),'persona_hash':digest(engine.s['personas']),
            'exogenous_hash':digest(engine.s['latent']),'statistical_unit':'paired_world',
            'source_fingerprint':digest(source_hashes)}
        if c['mode']=='codex':
            from .doctor import fingerprint,gate_valid
            manifest['isolation_gate']={'passed_at_creation':gate_valid(),'fingerprint':fingerprint()}
            manifest['cli_version']=manifest['isolation_gate']['fingerprint']['cli_version']
        with (self.tx() if db is None else contextlib.nullcontext(db)) as db:
            db.execute('INSERT INTO runs(id,config,initial,state,state_hash,status,created,updated,parent,parent_seq,budget) '
                'VALUES(?,?,?,?,?,?,?,?,?,?,?)',(run,canonical(c),canonical(engine.s),canonical(engine.s),
                engine.hash(),'CREATED',now,now,parent,engine.s['seq'] if parent else None,c['attempt_budget']))
            db.execute('UPDATE runs SET manifest=? WHERE id=?',(canonical(manifest),run))
            db.execute('UPDATE runs SET controls=? WHERE id=?',(canonical({'breakpoints':c['breakpoints']}),run))
            db.execute('INSERT INTO checkpoints VALUES(?,?,?,?)',(run,engine.s['seq'],canonical(engine.s),engine.hash()))
        return run
    def get(self,run):
        with self.connect() as db: row=db.execute('SELECT * FROM runs WHERE id=?',(run,)).fetchone()
        if not row: raise KeyError(run)
        result=dict(row)
        for key in ('config','initial','state','manifest','controls'): result[key]=json.loads(result[key])
        if digest(result['state'])!=result['state_hash']: raise Conflict('STATE_HASH_CORRUPT')
        return result
    def list(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('SELECT id,status,created,updated,parent,error,budget,config FROM runs ORDER BY created DESC')]
    def control(self,run,command,budget=None):
        with self.tx() as db:
            row=db.execute('SELECT * FROM runs WHERE id=?',(run,)).fetchone()
            if not row: raise KeyError(run)
            if command=='step_event' and Engine(json.loads(row['state'])).ready():
                raise Conflict('DECISION_FRONTIER_REQUIRES_DECISION_STEP')
            inflight=db.execute("SELECT count(*) FROM jobs WHERE run=? AND status='spawned'",(run,)).fetchone()[0]
            if command in ('start','resume','step_event','step_decision'):
                if row['status']=='COMPLETED': raise Conflict('ALREADY_COMPLETED')
                if db.execute("SELECT count(*) FROM jobs WHERE run=? AND status='unknown'",(run,)).fetchone()[0]:
                    raise Conflict('UNKNOWN_REQUIRES_RESUBMIT')
                status='RUNNING'; step=command if command.startswith('step_') else None
            elif command=='pause': status='PAUSING' if inflight else 'PAUSED'; step=None
            elif command=='stop': status='STOPPED' if not inflight else 'STOPPING'; step=None
            elif command in ('resubmit_unknown','retry_failed'):
                if inflight: raise Conflict('INFLIGHT')
                old='unknown' if command=='resubmit_unknown' else 'failed'
                db.execute("UPDATE jobs SET status='queued',error=NULL,fence=(SELECT fence FROM runs WHERE id=jobs.run) WHERE run=? AND status=?",(run,old))
                status='PAUSED'; step=None
            elif command=='budget':
                if not isinstance(budget,int) or not row['budget']<budget<=100000: raise ValueError('BUDGET_MUST_INCREASE')
                db.execute('UPDATE runs SET budget=?,updated=? WHERE id=?',(budget,time.time(),run)); return
            else: raise ValueError('UNKNOWN_COMMAND')
            db.execute('UPDATE runs SET status=?,step=?,updated=?,error=NULL WHERE id=?',(status,step,time.time(),run))
    def save(self,run,engine,expected_hash,fence=None,commit_jobs=(),status=None):
        engine.invariants()
        with self.tx() as db:
            row=db.execute('SELECT state_hash,fence,status FROM runs WHERE id=?',(run,)).fetchone()
            if row['state_hash']!=expected_hash or (fence is not None and row['fence']!=fence):
                raise Conflict('STALE_WORLD_FENCE')
            db.execute('UPDATE runs SET state=?,state_hash=?,updated=? WHERE id=?',
                       (canonical(engine.s),engine.hash(),time.time(),run))
            for event in engine.events:
                db.execute('INSERT INTO events VALUES(?,?,?)',(run,event['seq'],canonical(event)))
            for job in commit_jobs:
                changed=db.execute("UPDATE jobs SET status='committed' WHERE id=? AND status='responded' AND fence=?",
                                   (job,row['fence'])).rowcount
                if changed!=1: raise Conflict('STALE_JOB_FENCE')
            if engine.s['seq']%50<len(engine.events) or status in ('PAUSED','COMPLETED','STOPPED'):
                db.execute('INSERT OR REPLACE INTO checkpoints VALUES(?,?,?,?)',
                           (run,engine.s['seq'],canonical(engine.s),engine.hash()))
            if status: db.execute('UPDATE runs SET status=?,step=NULL WHERE id=?',(status,run))
    def event_list(self,run,after=0,limit=500):
        with self.connect() as db:
            return [json.loads(r[0]) for r in db.execute('SELECT data FROM events WHERE run=? AND seq>? ORDER BY seq LIMIT ?',
                                                       (run,after,limit))]
    def jobs(self,run,frontier=None):
        query='SELECT * FROM jobs WHERE run=?'; values=[run]
        if frontier: query+=' AND frontier=?'; values.append(frontier)
        with self.connect() as db: rows=db.execute(query,values).fetchall()
        result=[]
        for row in rows:
            d=dict(row)
            for key in ('observation','memory','response','metadata'):
                if d[key] is not None: d[key]=json.loads(d[key])
            result.append(d)
        return result
    def prepare_jobs(self,run,engine,fence):
        frontier=engine.hash()
        with self.tx() as db:
            row=db.execute('SELECT state_hash,fence FROM runs WHERE id=?',(run,)).fetchone()
            if row['state_hash']!=frontier or row['fence']!=fence: raise Conflict('FRONTIER_CHANGED')
            for world,aid in engine.ready():
                job=digest([run,frontier,world,aid])
                db.execute('INSERT OR IGNORE INTO jobs(id,run,frontier,world,agent,observation,memory,status,fence) '
                    'VALUES(?,?,?,?,?,?,?,?,?)',(job,run,frontier,world,aid,canonical(engine.observation(world,aid)),
                    canonical(engine.s['worlds'][world]['agents'][aid]['memory']),'queued',fence))
        return self.jobs(run,frontier)
    def claim(self,job,fence):
        attempt='attempt-'+uuid.uuid4().hex; now=time.time()
        with self.tx() as db:
            row=db.execute('SELECT j.*,r.budget,r.status AS run_status,r.state_hash,r.fence AS current_fence FROM jobs j JOIN runs r ON r.id=j.run WHERE j.id=?',(job,)).fetchone()
            if not row or row['status']!='queued' or row['fence']!=fence or row['current_fence']!=fence or row['run_status']!='RUNNING': return None
            if row['state_hash']!=row['frontier']: raise Conflict('STALE_JOB')
            used=db.execute('SELECT count(*) FROM attempts WHERE run=?',(row['run'],)).fetchone()[0]
            if used>=row['budget']:
                db.execute("UPDATE runs SET status='PAUSED',error='BUDGET_EXHAUSTED' WHERE id=?",(row['run'],)); return None
            db.execute("UPDATE jobs SET status='spawned',lease_until=? WHERE id=?",(now+300,job))
            db.execute('INSERT INTO attempts(id,job,run,status,started) VALUES(?,?,?,?,?)',
                       (attempt,job,row['run'],'reserved',now))
        return attempt
    def spawned(self,attempt,pid,process_start):
        with self.tx() as db:
            db.execute("UPDATE attempts SET status='spawned',pid=?,process_start=? WHERE id=?",
                       (pid,process_start,attempt))
    def respond(self,job,attempt,fence,response,metadata,error=None,unknown=False):
        with self.tx() as db:
            row=db.execute('SELECT j.*,r.fence AS current_fence,r.state_hash FROM jobs j JOIN runs r ON r.id=j.run WHERE j.id=?',(job,)).fetchone()
            if not row or row['status']!='spawned' or row['fence']!=fence or row['current_fence']!=fence or row['state_hash']!=row['frontier']:
                raise Conflict('LATE_WORKER_RESULT')
            retry=error=='INVALID_RESPONSE' and not unknown and row['retries']<2
            status='queued' if retry else ('unknown' if unknown else ('failed' if error else 'responded'))
            db.execute('UPDATE jobs SET status=?,response=?,metadata=?,error=?,lease_until=NULL WHERE id=?',
                       (status,canonical(response) if response else None,canonical(metadata),error,job))
            db.execute('UPDATE attempts SET status=?,ended=?,metadata=? WHERE id=?',
                       ('unknown' if unknown else ('failed' if error else 'responded'),time.time(),canonical(metadata),attempt))
            if retry: db.execute('UPDATE jobs SET retries=retries+1 WHERE id=?',(job,))
            if error:
                if not retry: db.execute("UPDATE runs SET status='PAUSED',error=?,updated=? WHERE id=?",(error,time.time(),row['run']))
                db.execute('INSERT INTO issues VALUES(?,?,?,?,?,?,?,?,?)',
                    ('issue-'+uuid.uuid4().hex[:10],row['run'],None,error,'P1','open',
                     canonical({'job':job,'unknown':unknown}),time.time(),None))
    def attempts(self,run):
        with self.connect() as db: rows=db.execute('SELECT * FROM attempts WHERE run=? ORDER BY started',(run,)).fetchall()
        return [{**dict(r),'metadata':json.loads(r['metadata']) if r['metadata'] else None} for r in rows]
    def heartbeat(self,key,value):
        with self.tx() as db:
            db.execute('INSERT OR REPLACE INTO health VALUES(?,?,?)',(key,canonical(value),time.time()))
    def health(self):
        with self.connect() as db: rows=db.execute('SELECT * FROM health').fetchall()
        return {r['key']:{'value':json.loads(r['value']),'updated':r['updated'],
                         'age_seconds':round(time.time()-r['updated'],2)} for r in rows}
    def new_fence(self):
        with self.tx() as db:
            db.execute('UPDATE runs SET fence=fence+1')
            db.execute("UPDATE jobs SET status='unknown',error='CRASH_UNKNOWN' WHERE status='spawned'")
            db.execute("UPDATE attempts SET status='unknown',ended=? WHERE status IN ('reserved','spawned')",(time.time(),))
            db.execute("UPDATE runs SET status='PAUSED',error='CRASH_UNKNOWN' WHERE id IN (SELECT run FROM jobs WHERE status='unknown')")
            db.execute('UPDATE jobs SET fence=(SELECT fence FROM runs WHERE runs.id=jobs.run) WHERE status IN (\'queued\',\'responded\',\'unknown\',\'failed\')')
    def issue_list(self,run=None):
        with self.connect() as db:
            rows=db.execute('SELECT * FROM issues'+(' WHERE run=?' if run else '')+' ORDER BY created DESC',([run] if run else [])).fetchall()
        return [dict(r) for r in rows]

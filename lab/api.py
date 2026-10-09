from __future__ import annotations
import asyncio
import copy
import json
import os
import secrets
import time
import uuid
from contextlib import asynccontextmanager
import psutil
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import JSONResponse,Response,StreamingResponse
from pydantic import BaseModel,ConfigDict,Field
from .common import DATA,RunConfig,Costs,Targets,Decision,canonical,digest
from .engine import Engine
from .model import CAPABILITIES
from .reports import build_report,export_zip,html_report,replay
from .store import Store,Conflict
from .doctor import gate_valid

NONCE=secrets.token_urlsafe(32)
store=Store()

@asynccontextmanager
async def lifespan(app):
    async def heartbeat():
        while True:
            store.heartbeat('api',{'pid':os.getpid(),'rss_bytes':psutil.Process().memory_info().rss})
            await asyncio.sleep(5)
    task=asyncio.create_task(heartbeat())
    yield
    task.cancel()

app=FastAPI(title='Anywear synthetic consumer laboratory',version='0.1.0',lifespan=lifespan,
            docs_url=None,redoc_url=None)

@app.middleware('http')
async def local_only(request:Request,call_next):
    api_port=int(os.environ.get('ANYWEAR_LAB_API_PORT','8001'))
    web_port=int(os.environ.get('ANYWEAR_LAB_WEB_PORT','3001'))
    hosts={f'127.0.0.1:{api_port}',f'localhost:{api_port}','testserver'}
    if request.headers.get('host') not in hosts:
        return JSONResponse({'error':'HOST_DENIED'},status_code=403)
    origin=request.headers.get('origin')
    if origin and origin not in {f'http://localhost:{web_port}',f'http://127.0.0.1:{web_port}'}:
        return JSONResponse({'error':'ORIGIN_DENIED'},status_code=403)
    if request.method not in ('GET','HEAD','OPTIONS'):
        if not secrets.compare_digest(request.headers.get('x-lab-nonce',''),NONCE):
            return JSONResponse({'error':'NONCE_REQUIRED'},status_code=403)
        length=request.headers.get('content-length','0')
        if not length.isdigit() or int(length)>65536:
            return JSONResponse({'error':'BODY_TOO_LARGE'},status_code=413)
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'; response.headers['X-Content-Type-Options']='nosniff'
    return response

@app.exception_handler(Conflict)
async def conflict(request,error): return JSONResponse({'error':str(error)},status_code=409)
@app.exception_handler(KeyError)
async def missing(request,error): return JSONResponse({'error':'NOT_FOUND'},status_code=404)
@app.exception_handler(ValueError)
async def invalid(request,error): return JSONResponse({'error':str(error)[:100]},status_code=400)

@app.get('/api/lab/session')
def session(): return {'nonce':NONCE,'schema_version':1,'capabilities':CAPABILITIES}

@app.get('/api/lab/health')
def health():
    services=store.health(); disk=psutil.disk_usage(DATA); alarms=[]
    for key in ('api','worker'):
        if key not in services or services[key]['age_seconds']>15 or services[key]['value'].get('stopped'):
            alarms.append({'code':key.upper()+'_STALE','severity':'warning'})
    if disk.free<500_000_000: alarms.append({'code':'LOW_DISK','severity':'critical'})
    path=DATA/'isolation-gate.json'; gate=json.loads(path.read_text()) if path.exists() else {'passed':False}
    return {'services':services,'alarms':alarms,'disk_free_bytes':disk.free,'memory_available_bytes':psutil.virtual_memory().available,
            'isolation_gate':{'passed':gate_valid(),'observed_utc':gate.get('observed_utc')},
            'monetary_cost':None,'model':'gpt-6.1-sol','local_only':True}

@app.get('/api/lab/runs')
def runs():
    rows=store.list()
    for row in rows: row['config']=json.loads(row['config'])
    return rows

@app.post('/api/lab/runs')
def create(config:RunConfig):
    return {'run_id':store.create(config.model_dump())}

@app.get('/api/lab/runs/{run}/state')
def state(run:str,request:Request):
    row=store.get(run)
    if request.headers.get('if-none-match')==row['state_hash']: return Response(status_code=304)
    current=Engine(row['state']).public()
    for world in current['worlds'].values():
        for agent in world['agents'].values(): agent['memory']=agent['memory'][-8:]
    return JSONResponse({'run_id':run,'status':row['status'],'error':row['error'],'parent':row['parent'],'parent_seq':row['parent_seq'],
        'controls':row['controls'],'budget':row['budget'],'state':current,'manifest':row['manifest'],
        'updated_wall_ms':round(row['updated']*1000)},
        headers={'ETag':row['state_hash']})

@app.get('/api/lab/runs/{run}/agents/{world}/{agent}')
def agent_detail(run:str,world:str,agent:str):
    row=store.get(run); engine=Engine(row['state'])
    return {'consumer':row['state']['worlds'][world]['agents'][agent],
            'visible_observation':engine.observation(world,agent),
            'goal_source':'synthetic_ground_truth','logical_context_id':f'{run}/{world}/{agent}'}

class Command(BaseModel):
    model_config=ConfigDict(extra='forbid')
    command:str
    budget:int|None=None
    breakpoints:list[str]|None=None

@app.post('/api/lab/runs/{run}/control')
def control(run:str,body:Command):
    if body.command=='breakpoints':
        allowed={'PURCHASED','LEFT','QUEUE_JOINED','INVALID','GOAL_MET'}
        if not set(body.breakpoints or [])<=allowed: raise ValueError('INVALID_BREAKPOINT')
        with store.tx() as db:
            db.execute('UPDATE runs SET controls=? WHERE id=?',(canonical({'breakpoints':body.breakpoints or []}),run))
    else: store.control(run,body.command,body.budget)
    return {'ok':True,'status':store.get(run)['status']}

@app.get('/api/lab/runs/{run}/events')
def events(run:str,after:int=0,limit:int=200):
    return [{**e,'run_id':run,'branch_id':run} for e in store.event_list(run,max(0,after),max(1,min(limit,1000)))]

@app.get('/api/lab/runs/{run}/stream')
async def stream(run:str,request:Request,after:int=0):
    store.get(run)
    try: cursor=max(after,int(request.headers.get('last-event-id','0')))
    except ValueError: cursor=after
    async def generate():
        nonlocal cursor
        while not await request.is_disconnected():
            rows=store.event_list(run,cursor,200)
            for event in rows:
                cursor=event['seq']; payload={**event,'run_id':run,'branch_id':run}
                yield f'id: {cursor}\nevent: world\ndata: {canonical(payload)}\n\n'
            if not rows:
                row=store.get(run)
                yield f'event: heartbeat\ndata: {canonical({"status":row["status"],"seq":row["state"]["seq"]})}\n\n'
            await asyncio.sleep(.5)
    return StreamingResponse(generate(),media_type='text/event-stream',headers={'X-Accel-Buffering':'no'})

@app.get('/api/lab/runs/{run}/report')
def report(run:str,analysis_id:str|None=None): return build_report(store,run,analysis_id)

@app.get('/api/lab/runs/{run}/export')
def export(run:str):
    return Response(export_zip(store,run),media_type='application/zip',
                    headers={'Content-Disposition':f'attachment; filename="{run}-report.zip"'})

@app.get('/api/lab/runs/{run}/report.html')
def standalone_report(run:str): return Response(html_report(build_report(store,run)),media_type='text/html')

@app.get('/api/lab/runs/{run}/replay')
def replay_run(run:str,seq:int|None=None): return replay(store,run,seq)

class Fork(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_hash:str
    patch:dict=Field(default_factory=dict)
    world:str|None=None
    agent:str|None=None
    decision:Decision|None=None
    at_seq:int|None=None

@app.post('/api/lab/runs/{run}/fork')
def fork(run:str,body:Fork):
    row=store.get(run)
    if row['state_hash']!=body.expected_hash: raise Conflict('STALE_SNAPSHOT')
    if row['status'] not in ('PAUSED','CREATED','COMPLETED','STOPPED','INCOMPLETE'): raise Conflict('PAUSE_BEFORE_FORK')
    if any(j['status']=='spawned' for j in store.jobs(run)): raise Conflict('INFLIGHT')
    allowed={'price_cents','stock_per_sku','arrival_seconds','fitting_rooms','preview_devices','checkout_desks',
             'preview_noise','fitting_seconds','preview_seconds','checkout_seconds','browse_seconds'}
    if not set(body.patch)<=allowed: raise ValueError('INITIAL_CONDITION_REQUIRES_NEW_RUN')
    config=RunConfig.model_validate({**row['config'],**body.patch,'name':row['config']['name']+' · branch'}).model_dump()
    if body.at_seq is not None and not row['initial']['seq']<=body.at_seq<=row['state']['seq']:
        raise ValueError('INVALID_REPLAY_SEQ')
    copied=(replay(store,run,body.at_seq,internal=True)['internal_state'] if body.at_seq is not None else copy.deepcopy(row['state']))
    copied['config']=config
    for world in copied['worlds'].values():
        for key,field in [('fitting','fitting_rooms'),('preview','preview_devices'),('checkout','checkout_desks')]:
            r=world['resources'][key]; capacity=config[field] if r['capacity'] else 0
            if len(r['busy'])>capacity or any(int(slot)>=capacity for slot in r['busy']): raise Conflict('CAPACITY_BELOW_ACTIVE_SERVICE')
            r['capacity']=capacity
        for item in world['stock'].values():
            new_available=config['stock_per_sku']-item['reserved']-item['sold']
            if new_available<0: raise Conflict('STOCK_BELOW_COMMITTED')
            item.update(initial=config['stock_per_sku'],available=new_available)
    # Reschedule only shoppers who have not entered the observation window.
    for world_id,world in copied['worlds'].items() if 'arrival_seconds' in body.patch else []:
        future=sorted([a for a in world['agents'].values() if a['status']=='NOT_ARRIVED'],key=lambda a:a['arrival'])
        for index,agent in enumerate(future):
            arrival=max(copied['t']+1,future[0]['arrival'])+index*config['arrival_seconds']
            agent['arrival']=arrival; agent['deadline']=arrival+copied['personas'][agent['id']]['remaining_seconds']
            for event in copied['agenda']:
                if event['world']==world_id and event['agent']==agent['id']:
                    if event['kind']=='arrival': event['t']=arrival
                    elif event['kind']=='deadline': event['t']=agent['deadline']
    if body.decision:
        if not body.world or not body.agent: raise ValueError('MANUAL_TARGET_REQUIRED')
        engine=Engine(copied)
        if (body.world,body.agent) not in engine.ready(): raise Conflict('MANUAL_TARGET_NOT_READY')
        if {'action':body.decision.action,'sku':body.decision.sku} not in engine.actions(body.world,body.agent):
            raise ValueError('INVALID_MANUAL_ACTION')
    child=store.create(config,parent=run,state=copied)
    if body.decision:
        if not body.world or not body.agent: raise ValueError('MANUAL_TARGET_REQUIRED')
        engine=Engine(copied)
        if (body.world,body.agent) not in engine.ready(): raise Conflict('MANUAL_TARGET_NOT_READY')
        jobs=store.prepare_jobs(child,engine,0)
        target=next(j for j in jobs if (j['world'],j['agent'])==(body.world,body.agent))
        if {'action':body.decision.action,'sku':body.decision.sku} not in target['observation']['allowed_actions']:
            raise ValueError('INVALID_MANUAL_ACTION')
        with store.tx() as db:
            db.execute("UPDATE jobs SET status='responded',response=?,metadata=? WHERE id=?",
                       (body.decision.model_dump_json(),canonical({'mode':'manual','source':'operator_intervention'}),target['id']))
            manifest=store.get(child)['manifest']; manifest['manual_intervention']={'world':body.world,'agent':body.agent}
            db.execute('UPDATE runs SET manifest=? WHERE id=?',(canonical(manifest),child))
    return {'run_id':child,'parent':run,'exploratory':True}

class Analysis(BaseModel):
    model_config=ConfigDict(extra='forbid')
    costs:Costs
    targets:Targets

@app.post('/api/lab/runs/{run}/analyses')
def analyze(run:str,body:Analysis):
    row=store.get(run); analysis='analysis-'+uuid.uuid4().hex[:10]
    with store.tx() as db:
        db.execute('INSERT INTO analyses VALUES(?,?,?,?,?)',(analysis,run,body.model_dump_json(),time.time(),int(row['state']['seq']>0)))
    return {'analysis_id':analysis,'model_calls':0,'report':build_report(store,run,analysis)}

@app.get('/api/lab/issues')
def issues(run:str|None=None): return store.issue_list(run)

@app.get('/api/lab/runs/{run}/debug')
def debug(run:str):
    row=store.get(run)
    jobs=store.jobs(run)
    from collections import Counter
    return {'job_counts':dict(Counter(j['status'] for j in jobs)),'run_id':run,'state_hash':row['state_hash'],'fence':row['fence'],'error':row['error'],
        'jobs':[{k:j[k] for k in ('id','world','agent','status','frontier','error','retries')} for j in ([j for j in jobs if j['status']!='committed']+[j for j in jobs if j['status']=='committed'][-20:])],
        'issues':store.issue_list(run),'invariants':Engine(row['state']).invariants()}

class Batch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind:str
    config:RunConfig

@app.post('/api/lab/batches')
def create_batch(body:Batch):
    if body.kind not in ('sensitivity','replicates'): raise ValueError('INVALID_BATCH_KIND')
    base=body.config.model_dump()
    cells=([{'price_cents':p,'initial_fitting_delay':q,'seed':base['seed']} for p in (3000,12000,30000) for q in (0,900,1800)]
           if body.kind=='sensitivity' else [{'seed':base['seed']+i} for i in range(10)])
    cells=[{**cell,'run_id':None,'status':'NOT_RUN'} for cell in cells]
    batch='batch-'+uuid.uuid4().hex[:10]
    with store.tx() as db:
        db.execute('INSERT INTO batches VALUES(?,?,?,?,?)',(batch,body.kind,canonical(base),canonical(cells),time.time()))
    return {'batch_id':batch,'cells':cells,'maximum_cli_attempts':len(cells)*base['attempt_budget'],'started':False}

@app.get('/api/lab/batches')
def batches():
    with store.connect() as db: rows=db.execute('SELECT * FROM batches ORDER BY created DESC').fetchall()
    results=[]
    for row in rows:
        d=dict(row); d['config']=json.loads(d['config']); d['cells']=json.loads(d['cells'])
        for cell in d['cells']:
            if cell['run_id']:
                r=build_report(store,cell['run_id']); cell.update(status=r['status'],complete=r['complete'],
                    purchase_delta=r['deltas']['purchase_rate'],goal=r['goals']['status'])
        d['maximum_cli_attempts']=len(d['cells'])*d['config']['attempt_budget']; results.append(d)
    return results

@app.post('/api/lab/batches/{batch}/start')
def start_batch(batch:str):
    # The launch and every run record commit together. A crash cannot create an unlinked run.
    with store.tx() as db:
        row=db.execute('SELECT * FROM batches WHERE id=?',(batch,)).fetchone()
        if not row: raise KeyError(batch)
        base=json.loads(row['config']); cells=json.loads(row['cells'])
        if any(c['run_id'] for c in cells): raise Conflict('BATCH_ALREADY_STARTED')
        for index,cell in enumerate(cells):
            config={**base,**{k:v for k,v in cell.items() if k not in ('run_id','status')},'name':f'{row["kind"]} {index+1}'}
            cell['run_id']=store.create(config,db=db); cell['status']='RUNNING'
            db.execute("UPDATE runs SET status='RUNNING' WHERE id=?",(cell['run_id'],))
        db.execute('UPDATE batches SET cells=? WHERE id=?',(canonical(cells),batch))
    return {'started':True,'cells':cells}

@app.get('/api/lab/batches/{batch}/statistics')
def batch_statistics(batch:str):
    with store.connect() as db: row=db.execute('SELECT * FROM batches WHERE id=?',(batch,)).fetchone()
    if not row: raise KeyError(batch)
    cells=json.loads(row['cells']); reports=[build_report(store,c['run_id']) for c in cells if c['run_id']]
    if row['kind']!='replicates' or len(reports)<10 or not all(r['formal_comparison_eligible'] for r in reports):
        return {'status':'insufficient_data','unit':'paired_world','planned_cells':len(cells),'complete_cells':sum(r['complete'] for r in reports),'ci':None}
    import numpy as np
    rng=np.random.default_rng(20261009); values=np.array([r['deltas']['purchase_rate'] for r in reports])
    samples=np.mean(rng.choice(values,size=(10000,len(values)),replace=True),axis=1)
    return {'status':'simulated_world_interval','unit':'paired_world','n_pairs':len(values),
        'purchase_delta_mean':float(values.mean()),'ci95':[float(np.quantile(samples,.025)),float(np.quantile(samples,.975))],
        'real_market_evidence':False}

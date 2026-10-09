import json
import pytest
from fastapi.testclient import TestClient
from lab import api
from lab.store import Store
from lab.engine import Engine
from lab.reports import replay
from lab.tests.test_lab import run_demo

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(api,'store',Store(tmp_path/'api.db'))
    with TestClient(api.app) as client:
        client.headers['x-lab-nonce']=client.get('/api/lab/session').json()['nonce']
        yield client

def test_local_origin_and_write_nonce(client):
    assert client.post('/api/lab/runs',json={},headers={'Origin':'https://evil.example'}).status_code==403
    assert client.post('/api/lab/runs',json={},headers={'x-lab-nonce':''}).status_code==403
    assert client.get('/api/lab/health',headers={'Host':'evil.example'}).status_code==403
    assert client.post('/api/lab/runs',json={}).status_code==200

def test_branch_replay_and_invalid_manual_has_no_side_effect(client):
    parent=run_demo(api.store,3); row=api.store.get(parent)
    before=len(api.store.list())
    invalid=client.post(f'/api/lab/runs/{parent}/fork',json={'expected_hash':row['state_hash'],
        'world':'control','agent':'C001','decision':{'action':'leave','sku':'','reason_code':'no_options','reason_zh':'测试','reason_en':'Test'}})
    assert invalid.status_code==409 and len(api.store.list())==before
    response=client.post(f'/api/lab/runs/{parent}/fork',json={'expected_hash':row['state_hash'],'at_seq':3,'patch':{'price_cents':3000}})
    assert response.status_code==200,response.text
    child=response.json()['run_id']; c=api.store.get(child)
    assert api.store.get(parent)['state_hash']==row['state_hash']
    assert c['initial']['seq']>=3 and c['parent']==parent
    assert not api.store.jobs(child) and c['initial']['latent']==row['initial']['latent']
    assert replay(api.store,child)['matched_saved_state']

def test_batch_launch_atomic_and_does_not_start_on_plan(client,monkeypatch):
    batch=client.post('/api/lab/batches',json={'kind':'sensitivity','config':{'n_agents':1}}).json()
    assert batch['maximum_cli_attempts']==1800 and len(api.store.list())==0
    original=api.store.create; calls=0
    def fail_after_one(*args,**kwargs):
        nonlocal calls
        calls+=1
        if calls==2: raise ValueError('INJECTED_TRANSACTION_FAILURE')
        return original(*args,**kwargs)
    monkeypatch.setattr(api.store,'create',fail_after_one)
    response=client.post(f'/api/lab/batches/{batch["batch_id"]}/start',json={})
    assert response.status_code==400 and not api.store.list()
    assert all(c['run_id'] is None for c in client.get('/api/lab/batches').json()[0]['cells'])
    monkeypatch.setattr(api.store,'create',original)
    assert client.post(f'/api/lab/batches/{batch["batch_id"]}/start',json={}).status_code==200
    assert len(api.store.list())==9
    assert client.post(f'/api/lab/batches/{batch["batch_id"]}/start',json={}).status_code==409

def test_cost_analysis_is_versioned_without_calls(client):
    run=run_demo(api.store,2); before=len(api.store.attempts(run)); original=api.store.get(run)['state_hash']
    r=client.post(f'/api/lab/runs/{run}/analyses',json={'costs':{'cogs_cents':1000},'targets':{}}).json()
    assert r['model_calls']==0 and r['report']['goals']['post_hoc']
    assert len(api.store.attempts(run))==before and api.store.get(run)['state_hash']==original

def test_wait_estimate_respects_free_slots_and_own_position():
    e=Engine.create({'n_agents':2}); e.advance(); r=e.s['worlds']['control']['resources']['fitting']
    r['busy']={'0':{'until':180}}
    assert e.observation('control','C001')['resources']['fitting']['estimated_wait_seconds']==0
    r['capacity']=1;r['queue']=[{'agent':'C001'},{'agent':'C002'}]
    assert e.observation('control','C001')['resources']['fitting']['estimated_wait_seconds']==180
    assert e.observation('control','C002')['resources']['fitting']['estimated_wait_seconds']==360

def test_unknown_attempt_stays_unknown(tmp_path):
    s=Store(tmp_path/'unknown.db');run=s.create({'n_agents':1});s.control(run,'start')
    e=Engine(s.get(run)['state']);e.advance();s.save(run,e,s.get(run)['state_hash'])
    job=s.prepare_jobs(run,e,0)[0]; attempt=s.claim(job['id'],0)
    s.respond(job['id'],attempt,0,None,{},'TIMEOUT_UNKNOWN',True)
    assert s.attempts(run)[0]['status']=='unknown'
    assert s.get(run)['status']=='PAUSED'
    assert s.claim(job['id'],0) is None

def test_failed_job_can_retry_after_restart(tmp_path):
    s=Store(tmp_path/'retry.db');run=s.create({'n_agents':1});s.control(run,'start')
    e=Engine(s.get(run)['state']);e.advance();s.save(run,e,s.get(run)['state_hash'])
    job=s.prepare_jobs(run,e,0)[0];attempt=s.claim(job['id'],0)
    s.respond(job['id'],attempt,0,None,{},'PROVIDER_ERROR')
    s.new_fence();s.control(run,'retry_failed');s.control(run,'resume')
    updated=next(j for j in s.jobs(run) if j['id']==job['id'])
    assert updated['fence']==s.get(run)['fence']==1
    assert s.claim(job['id'],0) is None
    retry=s.claim(job['id'],1); assert retry
    s.respond(job['id'],retry,1,{'action':'leave'}, {})
    assert next(j for j in s.jobs(run) if j['id']==job['id'])['status']=='responded'

def test_single_event_does_not_invoke_model_at_frontier(tmp_path):
    from lab.store import Conflict
    s=Store(tmp_path/'step.db');run=s.create({'n_agents':1});s.control(run,'start')
    e=Engine(s.get(run)['state']);e.advance();s.save(run,e,s.get(run)['state_hash'])
    s.control(run,'pause')
    with pytest.raises(Conflict,match='DECISION_FRONTIER'):
        s.control(run,'step_event')
    assert s.get(run)['status']=='PAUSED' and not s.attempts(run)

import copy
import json
import pytest
from lab.common import Decision,digest,personas
from lab.engine import Engine,demo_decision
from lab.model import guarded_body,SYSTEM
from lab.agents import decide
from lab.store import Store,Conflict
from lab.worker import drive,execute
from lab.reports import build_report,replay,export_zip

def run_demo(store,n=10):
    run=store.create({'n_agents':n,'mode':'demo','attempt_budget':2000})
    store.control(run,'start')
    for _ in range(6000):
        drive(store,run); row=store.get(run)
        if row['status'] in ('COMPLETED','INCOMPLETE'): return run
        assert row['status']=='RUNNING', row.get('error')
        for job in store.jobs(run,row['state_hash']):
            if job['status']=='queued':
                attempt=store.claim(job['id'],job['fence'])
                assert attempt
                execute(store,job,attempt,row['config'])
    raise AssertionError('did not terminate')

def test_same_time_step_preserves_frontier():
    normal=Engine.create({'n_agents':2}); normal.advance()
    stepped=Engine.create({'n_agents':2}); stepped.advance(one_event=True)
    assert not stepped.ready()
    stepped.advance(one_event=True)
    assert stepped.hash()==normal.hash()
    assert len(stepped.ready())==2

def test_paired_private_observation_and_fixed_population():
    engine=Engine.create({'n_agents':10}); engine.advance()
    a=engine.observation('control','C001'); b=engine.observation('anywear','C001')
    assert a['persona']==b['persona']==personas(20261009)[0]
    assert 'fit' not in json.dumps(a['catalogue'])
    assert 'latent' not in json.dumps(a)
    assert 'C002' not in json.dumps(a)
    assert all(x['action']!='preview' for x in a['allowed_actions'])
    assert any(x['action']=='preview' for x in b['allowed_actions'])

def test_gateway_removes_injected_context_and_tools():
    malicious={'instructions':'OTHER_SHOPPER_SECRET','input':[{'role':'user','content':'OTHER_SHOPPER_SECRET'}],
        'tools':[{'type':'function','name':'read_files'}],'previous_response_id':'secret-history'}
    clean=guarded_body(malicious,'ONLY_CURRENT_SHOPPER',Decision.model_json_schema(),'gpt-6.1-sol')
    assert clean['tools']==[] and clean['tool_choice']=='none'
    assert clean['instructions']==SYSTEM
    assert 'OTHER_SHOPPER_SECRET' not in json.dumps(clean)
    assert 'previous_response_id' not in clean
    assert len(clean['input'])==1

def test_concordia_only_one_call_and_stable_memory():
    engine=Engine.create({'n_agents':1}); engine.advance()
    obs=engine.observation('control','C001'); memory=engine.s['worlds']['control']['agents']['C001']['memory']
    class Fixture:
        calls=0
        def sample_text(self,prompt):
            self.calls+=1; assert 'C002' not in prompt
            return json.dumps(demo_decision(obs))
    model=Fixture(); decision,metadata=decide(obs,memory,model)
    assert model.calls==1 and metadata['phase']=='READY'
    assert decide(obs,memory,Fixture())[1]['component_hashes']==metadata['component_hashes']

def test_last_stock_competition_and_reservation_release():
    engine=Engine.create({'n_agents':2,'stock_per_sku':1,'arrival_seconds':1,'price_cents':3000})
    engine.advance()
    d={'action':'buy','sku':'S1','reason_code':'suitable','reason_zh':'测试','reason_en':'Test'}
    engine.apply('control','C001',d)
    # Give second shopper a frozen pre-competition allowance, then resolve stock race.
    a=engine.s['worlds']['control']['agents']['C002']; a.update(status='DECIDING',ready=True,arrival=0)
    engine.apply('control','C002',d,allowed=[{'action':'buy','sku':'S1'}])
    assert engine.events[-1]['kind']=='STOCKOUT'
    engine.finish('control','C001','TIME_LIMIT')
    assert engine.s['worlds']['control']['stock']['S1']=={'initial':1,'available':1,'reserved':0,'sold':0}
    assert engine.invariants()

def test_budget_reservation_and_fencing(tmp_path):
    store=Store(tmp_path/'lab.db'); run=store.create({'n_agents':1,'attempt_budget':1})
    store.control(run,'start'); drive(store,run)
    row=store.get(run); jobs=store.prepare_jobs(run,Engine(row['state']),row['fence'])
    attempt=store.claim(jobs[0]['id'],0); assert attempt
    assert store.claim(jobs[1]['id'],0) is None
    assert store.get(run)['status']=='PAUSED'
    store.new_fence()
    with pytest.raises(Conflict): store.respond(jobs[0]['id'],attempt,0,{}, {})
    assert store.get(run)['error']=='CRASH_UNKNOWN'
    assert len(store.attempts(run))==1

def test_full_demo_report_replay_and_safe_export(tmp_path):
    import io,zipfile
    store=Store(tmp_path/'lab.db'); run=run_demo(store)
    report=build_report(store,run)
    assert report['complete'] and report['mode']=='demo'
    assert report['usage']['cli_attempts']==0
    assert all(w['natural_terminal']==10 for w in report['worlds'].values())
    replayed=replay(store,run)
    assert replayed['matched_saved_state'] and replayed['replay_calls']==0
    archive=zipfile.ZipFile(io.BytesIO(export_zip(store,run)))
    assert set(archive.namelist())=={'report.json','report.md','report.html','consumers.csv','events.csv','events.json','config.json','README.txt'}

def test_incomplete_is_not_leave_or_roi(tmp_path):
    store=Store(tmp_path/'lab.db'); run=store.create({'n_agents':10})
    report=build_report(store,run)
    assert not report['complete'] and report['goals']['status']=='insufficient_data'
    assert report['worlds']['control']['leave_rate']==0
    assert report['economics']['monthly_increment_cents'] is None
    assert report['usage']['input_tokens'] is None

def test_noop_agenda_is_replayable(tmp_path):
    store=Store(tmp_path/'noop.db');run=store.create({'n_agents':1,'initial_fitting_delay':1})
    e=Engine(store.get(run)['state']);before=e.hash();e.advance();store.save(run,e,before)
    e.events=[]
    frozen={(w,a):e.actions(w,a) for w,a in e.ready()}
    for w,a in e.ready():
        e.apply(w,a,{'action':'browse','sku':'S1','reason_code':'style','reason_zh':'测试','reason_en':'Test'},frozen[(w,a)])
    store.save(run,e,store.get(run)['state_hash'])
    before=e.hash();seq=e.s['seq'];e.advance(one_event=True);store.save(run,e,before)
    assert e.s['t']==1 and e.s['seq']>seq
    assert replay(store,run)['matched_saved_state']

def test_checkout_queue_can_abandon_and_release_stock():
    e=Engine.create({'n_agents':1,'price_cents':3000});e.advance()
    w=e.s['worlds']['control'];a=w['agents']['C001'];r=w['resources']['checkout']
    r['external_until']=1000
    w['stock']['S1']['available']-=1;w['stock']['S1']['reserved']+=1
    a.update(reserved_sku='S1',reserved_price=3000)
    e.enqueue('control','C001','checkout','S1')
    assert any(x['kind']=='reminder' and x['agent']=='C001' for x in e.s['agenda'])
    a['ready']=True
    e.apply('control','C001',{'action':'leave','sku':'','reason_code':'queue','reason_zh':'队伍过长','reason_en':'Queue too long'})
    assert w['stock']['S1']['reserved']==0 and w['stock']['S1']['available']==20
    assert not r['queue'] and a['status']=='LEFT' and e.invariants()

def test_world_event_breakpoint_pauses_at_commit(tmp_path):
    store=Store(tmp_path/'break.db');run=store.create({'n_agents':1,'price_cents':3000,'breakpoints':['QUEUE_JOINED']})
    store.control(run,'start');drive(store,run)
    row=store.get(run);e=Engine(row['state']);e.events=[]
    for w,a in e.ready():
        e.apply(w,a,{'action':'buy','sku':'S1','reason_code':'suitable','reason_zh':'测试','reason_en':'Test'})
    store.save(run,e,row['state_hash']);drive(store,run)
    assert store.get(run)['status']=='PAUSED'
    assert any(e['kind']=='QUEUE_JOINED' for e in store.event_list(run))
    assert not store.attempts(run)

def test_formal_qualification_excludes_demo_and_historical_unknown(tmp_path):
    store=Store(tmp_path/'formal.db');run=run_demo(store,1)
    assert build_report(store,run)['complete']
    assert not build_report(store,run)['formal_comparison_eligible']
    with store.tx() as db:
        config=store.get(run)['config'];config['mode']='codex'
        db.execute('UPDATE runs SET config=? WHERE id=?',(json.dumps(config),run))
        db.execute("UPDATE attempts SET status='unknown',metadata=? WHERE run=?",(json.dumps({'mode':'codex','cli_usage':{'output_tokens':12}}),run))
    report=build_report(store,run)
    assert report['complete'] and not report['formal_comparison_eligible']
    assert 'historical_unknown_attempt' in report['formal_exclusions']
    assert report['usage']['input_tokens'] is None
    assert report['usage']['missing_input_token_attempts']>0


def test_stop_censors_releases_and_replays_without_calls(tmp_path):
    s=Store(tmp_path/'stop.db');r=s.create({'n_agents':2,'price_cents':3000})
    s.control(r,'start');drive(s,r)
    row=s.get(r);e=Engine(row['state']);e.events=[]
    for w,a in e.ready():
        e.apply(w,a,{'action':'buy','sku':'S1','reason_code':'suitable','reason_zh':'测试','reason_en':'Test'})
    s.save(r,e,row['state_hash']);drive(s,r)
    entered_before={w:m['entered'] for w,m in build_report(s,r)['worlds'].items()}
    s.control(r,'stop');row=s.get(r)
    assert row['status']=='STOPPED' and not row['state']['agenda']
    assert all(a['status']=='CENSORED' for w in row['state']['worlds'].values() for a in w['agents'].values())
    assert Engine(row['state']).invariants()
    assert replay(s,r)['matched_saved_state']
    report=build_report(s,r)
    assert not report['complete'] and not report['formal_comparison_eligible']
    assert all(w['left']==0 and w['censored']==2 for w in report['worlds'].values())
    assert all(m['entered']==entered_before[w] for w,m in report['worlds'].items())
    assert report['economics']['monthly_increment_cents'] is None
    with pytest.raises(Conflict,match='RUN_STOPPED_CREATE_NEW'): s.control(r,'resume')
    seq=row['state']['seq'];s.control(r,'stop');assert s.get(r)['state']['seq']==seq


def test_stop_waits_for_inflight_and_survives_unknown_and_restart(tmp_path):
    s=Store(tmp_path/'stop-inflight.db');r=s.create({'n_agents':1})
    s.control(r,'start');drive(s,r);row=s.get(r)
    job=s.prepare_jobs(r,Engine(row['state']),row['fence'])[0]
    attempt=s.claim(job['id'],row['fence']);s.control(r,'stop')
    assert s.get(r)['status']=='STOPPING'
    assert s.claim(s.jobs(r)[1]['id'],row['fence']) is None
    s.respond(job['id'],attempt,row['fence'],None,{},'TIMEOUT',unknown=True)
    assert s.get(r)['status']=='STOPPING'
    s.new_fence();assert s.get(r)['status']=='STOPPING'
    drive(s,r);assert s.get(r)['status']=='STOPPED'
    assert s.attempts(r)[0]['status']=='unknown'
    assert build_report(s,r)['usage']['unknown_attempts']==1
    with pytest.raises(Conflict): s.control(r,'resubmit_unknown')
    with pytest.raises(Conflict): s.respond(job['id'],attempt,row['fence'],{}, {})


def test_stop_before_arrival_keeps_entered_zero(tmp_path):
    s=Store(tmp_path/'not-arrived.db');r=s.create({'n_agents':10})
    s.control(r,'stop')
    assert all(m['entered']==0 and m['censored']==10 and m['left']==0 for m in build_report(s,r)['worlds'].values())
    assert replay(s,r)['matched_saved_state']


def test_stale_running_drive_cannot_override_stop(tmp_path,monkeypatch):
    s=Store(tmp_path/'race.db');r=s.create({'n_agents':1,'breakpoints':['LEFT']})
    s.control(r,'start');drive(s,r)
    original=s.prepare_jobs
    def race(run,engine,fence):
        jobs=original(run,engine,fence)
        attempts=[s.claim(j['id'],fence) for j in jobs]
        s.control(run,'stop');assert s.get(run)['status']=='STOPPING'
        for j,a in zip(jobs,attempts):
            d={'action':'leave','sku':'','reason_code':'fatigue','reason_zh':'测试','reason_en':'Test'}
            s.respond(j['id'],a,fence,d,{'mode':'demo'})
        return s.jobs(run,engine.hash())
    monkeypatch.setattr(s,'prepare_jobs',race)
    with pytest.raises(Conflict,match='CONTROL_STATE_CHANGED'): drive(s,r)
    assert s.get(r)['status']=='STOPPING'
    drive(s,r)
    p=build_report(s,r)
    assert s.get(r)['status']=='STOPPED' and p['usage']['valid_decisions']==0
    assert all(m['left']==0 and m['censored']==1 for m in p['worlds'].values())
    assert replay(s,r)['matched_saved_state']


def test_operator_stop_wait_is_censored_not_abandoned(tmp_path):
    s=Store(tmp_path/'censored-queue.db');r=s.create({'n_agents':1,'price_cents':3000})
    row=s.get(r);e=Engine(row['state']);e.advance()
    for w in e.s['worlds']:
        e.s['worlds'][w]['resources']['checkout']['external_until']=1000
        e.enqueue(w,'C001','checkout','S1')
    e.s['t']=60
    s.save(r,e,row['state_hash']);s.control(r,'stop')
    p=build_report(s,r)
    for m in p['worlds'].values():
        assert m['closed_wait_episodes']==m['abandoned_wait_episodes']==0
        assert m['wait_p95_seconds'] is None
        assert m['censored_wait_episodes']==1 and m['observed_censored_wait_seconds']==[60]

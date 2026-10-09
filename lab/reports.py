from __future__ import annotations
import csv
import html
import io
import json
import statistics
import time
import zipfile
from collections import Counter
from .common import NATURAL, TERMINAL, WORLDS, Costs, Targets, canonical,digest,ROOT
from .engine import Engine

DEFINITIONS={
    'purchase_rate':'Payment committed / all planned consumers; model probability is not a purchase.',
    'leave_rate':'Voluntary LEFT plus personal TIME_LIMIT / all planned consumers. Technical censoring excluded and shown separately.',
    'suitable_rate':'Paid purchases with synthetic fit and appearance >= persona threshold, within budget/time / planned consumers.',
    'wait_percentiles':'Closed queue episodes, including served and abandoned, in virtual seconds; open episodes reported separately.',
    'utilization':'Consumer service seconds / (capacity * observed window); initial external occupation separate.',
    'statistical_unit':'Paired shared-store run, not individual shoppers.',
}

def quantile(values,p):
    if not values: return None
    ordered=sorted(values); position=(len(ordered)-1)*p; low=int(position); high=min(low+1,len(ordered)-1)
    return round(ordered[low]+(ordered[high]-ordered[low])*(position-low),2)

def world_metrics(state,world,costs):
    w=state['worlds'][world]; n=len(w['agents']); agents=list(w['agents'].values())
    counts=Counter(a['status'] for a in agents)
    natural=sum(counts[s] for s in NATURAL); paid=len(w['sales'])
    suitable=sum(bool(s['suitable']) for s in w['sales'])
    waits=[q['seconds'] for q in w['waits']]
    all_ended=all(a['status'] in NATURAL for a in agents)
    end=max([a['ended_at'] or 0 for a in agents]) if all_ended else state['t']
    window=max(0,end)
    utilization={}
    for resource,r in w['resources'].items():
        seconds=sum(s['end']-s['start'] for s in w['services'] if s['resource']==resource)
        seconds+=sum(max(0,state['t']-b['start']) for b in r['busy'].values())
        utilization[resource]={'consumer_fraction':round(seconds/max(1,window*r['capacity']),5),
            'initial_external_fraction':round(min(window,r['external_until'])/max(1,window),5),
            'queue_length':len(r['queue']),'busy':len(r['busy']),'capacity':r['capacity']}
    preview_count=sum(s['resource']=='preview' for s in w['services'])+len(w['resources']['preview']['busy'])
    revenue=sum(s['price_cents'] for s in w['sales'])
    return {'planned':n,'entered':n-counts['NOT_ARRIVED'],'natural_terminal':natural,
        'pending':n-natural-counts['CENSORED'],'censored':counts['CENSORED'],
        'paid':paid,'left':counts['LEFT'],'time_limit':counts['TIME_LIMIT'],'suitable':suitable,
        'purchase_rate':paid/n,'leave_rate':(counts['LEFT']+counts['TIME_LIMIT'])/n,'suitable_rate':suitable/n,
        'purchase_rate_possible_bounds':[paid/n,(paid+n-natural)/n],
        'status_counts':dict(counts),'wait_p50_seconds':quantile(waits,.5),'wait_p95_seconds':quantile(waits,.95),
        'closed_wait_episodes':len(waits),'abandoned_wait_episodes':sum(q['outcome']=='abandoned' for q in w['waits']),
        'open_wait_episodes':sum(a['queue'] is not None for a in agents),
        'window_seconds':window,'window_complete':all_ended,'resources':utilization,
        'preview_count':preview_count,'revenue_cents':revenue,
        'contribution_cents':revenue-paid*costs['cogs_cents']-preview_count*costs['preview_cents']}

def build_report(store,run,analysis_id=None):
    row=store.get(run); state=row['state']; config=row['config']
    settings={'costs':config['costs'],'targets':config['targets']}; post_hoc=False
    if analysis_id:
        with store.connect() as db:
            analysis=db.execute('SELECT * FROM analyses WHERE id=? AND run=?',(analysis_id,run)).fetchone()
        if not analysis: raise KeyError(analysis_id)
        settings=json.loads(analysis['settings']); post_hoc=bool(analysis['post_hoc'])
    costs=Costs.model_validate(settings['costs']).model_dump()
    targets=Targets.model_validate(settings['targets']).model_dump()
    worlds={w:world_metrics(state,w,costs) for w in WORLDS}
    a,b=worlds['control'],worlds['anywear']
    attempts=store.attempts(run); jobs=store.jobs(run)
    no_missing=all(j['status']=='committed' for j in jobs)
    complete=all(w['natural_terminal']==w['planned'] and w['censored']==0 for w in worlds.values()) and no_missing
    nominal_complete=row['status']=='COMPLETED' and complete
    formal_complete=(nominal_complete and config['mode']=='codex' and not row['parent']
        and not row['manifest'].get('manual_intervention') and not any(x['status']=='unknown' for x in attempts))
    monthly=round(costs['monthly_eligible']*(b['contribution_cents']/b['planned']-a['contribution_cents']/a['planned'])-costs['monthly_fixed_cents'])
    deltas={k:b[k]-a[k] for k in ('purchase_rate','leave_rate','suitable_rate','revenue_cents','contribution_cents')}
    met=(monthly>targets['min_monthly_increment_cents'] and
         deltas['leave_rate']<=targets['max_leave_delta'] and deltas['suitable_rate']>=targets['min_suitable_delta'])
    usage_rows=[x['metadata'].get('cli_usage') for x in attempts if x['metadata'] and x['metadata'].get('cli_usage')]
    usage={'cli_attempts':sum(x['metadata'] is None or x['metadata'].get('mode')!='demo' for x in attempts),
           'fixture_steps':sum(bool(x['metadata'] and x['metadata'].get('mode')=='demo') for x in attempts),
           'valid_decisions':sum(j['status']=='committed' for j in jobs),
           'failed_attempts':sum(x['status']=='failed' for x in attempts),
           'unknown_attempts':sum(x['status']=='unknown' for x in attempts),
           'responses_with_usage':len(usage_rows),'attempts_without_usage':sum(x['metadata'] is None or not x['metadata'].get('cli_usage') for x in attempts),
           'input_tokens':sum(u['input_tokens'] for u in usage_rows if 'input_tokens' in u) if any('input_tokens' in u for u in usage_rows) else None,
           'output_tokens':sum(u['output_tokens'] for u in usage_rows if 'output_tokens' in u) if any('output_tokens' in u for u in usage_rows) else None,
           'missing_input_token_attempts':sum(x['metadata'] is None or (x['metadata'].get('mode')!='demo' and 'input_tokens' not in (x['metadata'].get('cli_usage') or {})) for x in attempts),
           'missing_output_token_attempts':sum(x['metadata'] is None or (x['metadata'].get('mode')!='demo' and 'output_tokens' not in (x['metadata'].get('cli_usage') or {})) for x in attempts),
           'monetary_cost':None,'budget_cli_attempts':row['budget'],
           'observed_models':sorted({x['metadata']['actual_model'] for x in attempts if x['metadata'] and x['metadata'].get('actual_model')})}
    migration=[]
    for aid,p in state['personas'].items():
        control=state['worlds']['control']['agents'][aid]; treatment=state['worlds']['anywear']['agents'][aid]
        migration.append({'agent_id':aid,'budget_cents':p['budget_cents'],'trust':p['trust'],'privacy':p['privacy'],
            'control_status':control['status'],'anywear_status':treatment['status'],
            'control_goal':control['suitable'],'anywear_goal':treatment['suitable'],
            'control_decisions':control['decisions'],'anywear_decisions':treatment['decisions']})
    events=store.event_list(run,0,1000000)
    reasons={w:dict(Counter(e['data']['reason_code'] for e in events if e['world_id']==w and e['kind']=='DECISION')) for w in WORLDS}
    return {'schema_version':1,'run_id':run,'parent_run':row['parent'],'parent_seq':row['parent_seq'],
        'mode':config['mode'],'status':row['status'],'complete':nominal_complete,'formal_comparison_eligible':formal_complete,
        'formal_exclusions':(['demo_mode'] if config['mode']=='demo' else [])+(['branch_or_intervention'] if row['parent'] or row['manifest'].get('manual_intervention') else [])+(['historical_unknown_attempt'] if any(x['status']=='unknown' for x in attempts) else []),
        'exploratory':bool(row['parent'] or row['manifest'].get('manual_intervention')),
        'label':'DEMO rule fixture' if config['mode']=='demo' else 'Real model calls; synthetic consumers',
        'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(row['created'])),
        'state_hash':row['state_hash'],'initial_hash':digest(row['initial']),'config':config,
        'provenance':row.get('manifest',{}),'metric_definitions':DEFINITIONS,
        'worlds':worlds,'deltas':deltas,'usage':usage,'migration':migration,'stated_reasons':reasons,
        'economics':{'label':'Hypothetical scenario; not real-market ROI','costs':costs,
            'monthly_increment_cents':monthly if formal_complete else None,
            'payback_months':round(costs['capex_cents']/monthly,2) if formal_complete and monthly>0 else None,
            'roi_12_months':round((12*monthly-costs['capex_cents'])/costs['capex_cents'],5) if formal_complete and costs['capex_cents'] else None,
            'excluded':['returns/refunds','tax','labor','acquisition','simulation model monetary cost (unknown)']},
        'goals':{'status':('single_run_met_simulated' if met else 'not_met') if formal_complete else ('running' if row['status']=='RUNNING' else ('error' if row['error'] else 'insufficient_data')),
                 'targets':targets,'robustness':'not_tested','post_hoc':post_hoc,'analysis_id':analysis_id},
        'issues':store.issue_list(run),'limitations':[
            'Synthetic agents and assumed distributions; no real-market causal validation.',
            'One paired shared-store run is one experimental unit; no consumer-level independent CI.',
            'Initial 20 minutes and three failed trials are given history, not replayed observations.',
            'Replaying saved decisions is deterministic; repeating model calls is not guaranteed deterministic.',
            'CLI attempts are not a bound on upstream billing; missing usage is unknown, not zero.']}

def csv_bytes(rows):
    stream=io.StringIO(newline='')
    if rows:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader()
        for row in rows:
            clean={key:("'"+value if isinstance(value,str) and value.startswith(('=','+','-','@','\t','\r')) else value) for key,value in row.items()}
            writer.writerow(clean)
    return ('\ufeff'+stream.getvalue()).encode('utf-8')

def markdown(report):
    w=report['worlds']; a,b=w['control'],w['anywear']
    lines=['# Anywear 消费者实验报告 / Consumer experiment report',
        f"\nRun `{report['run_id']}` · {report['label']} · {report['status']}",
        f"\n完整 / complete: **{report['complete']}** · {report['goals']['status']}",
        '\n模型模拟，不是真实市场数据；经营数字为假设测算。',
        '\n|指标 / Metric|未提供 Anywear|提供 Anywear|', '|---|---:|---:|']
    for label,key in [('计划人数 / Planned','planned'),('自然终止 / Terminal','natural_terminal'),
        ('支付购买 / Paid','paid'),('主动离店 / Left','left'),('时间耗尽 / Time limit','time_limit'),
        ('技术截尾 / Censored','censored'),('达标购买 / Suitable','suitable'),
        ('排队p50秒 / Wait p50 s','wait_p50_seconds'),('排队p95秒 / Wait p95 s','wait_p95_seconds')]:
        lines.append(f'|{label}|{a[key]}|{b[key]}|')
    lines += ['\n## Usage / 调用',f"\n```json\n{json.dumps(report['usage'],ensure_ascii=False,indent=2)}\n```",
        '\n## Hypothetical economics / 假设经营测算',
        f"\n```json\n{json.dumps(report['economics'],ensure_ascii=False,indent=2)}\n```",
        '\n## Definitions / 指标口径']
    lines += [f'- {key}: {value}' for key,value in report['metric_definitions'].items()]
    lines += ['\n## Limitations / 限制']+[f'- {value}' for value in report['limitations']]
    lines += ['\n## Issues / 问题',f'\n{len(report["issues"])} recorded issues. See report.json for linked evidence.']
    return '\n'.join(lines)

def html_report(report):
    cards=''
    for world,title in [('control','未提供 Anywear / Without'),('anywear','提供 Anywear / With')]:
        m=report['worlds'][world]
        cards+=f'<section><h2>{title}</h2><p>{m["paid"]} / {m["planned"]} paid · {m["suitable"]} suitable</p>'
        for key in ('purchase_rate','leave_rate','suitable_rate'):
            cards+=f'<p>{key}: {m[key]:.1%}</p><div class="track"><i style="width:{100*m[key]:.2f}%"></i></div>'
        cards+='</section>'
    return ('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        '<title>Anywear experiment report</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 24px;color:#152d2d;background:#f3f5f0}'
        '.cards{display:flex;gap:24px}section{background:white;padding:24px;flex:1;border-radius:16px}.track{height:8px;background:#e3e9df}.track i{display:block;background:#317965;height:100%}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px ui-monospace}</style><h1>Anywear 实验报告</h1><p>模型模拟 · 非真实市场数据 · Hypothetical economics</p>'
        f'<div class="cards">{cards}</div><pre>{html.escape(markdown(report))}</pre><details><summary>完整报告 / Full report</summary><pre>'
        +html.escape(json.dumps(report,ensure_ascii=False,indent=2))+'</pre></details></html>')

def export_zip(store,run):
    report=build_report(store,run); events=store.event_list(run,0,1000000)
    event_rows=[{'seq':e['seq'],'virtual_time':e['virtual_time'],'world_id':e['world_id'],
                 'agent_id':e['agent_id'],'kind':e['kind'],'data':canonical(e['data'])} for e in events]
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('report.json',json.dumps(report,ensure_ascii=False,indent=2))
        z.writestr('report.md',markdown(report)); z.writestr('report.html',html_report(report))
        z.writestr('consumers.csv',csv_bytes(report['migration']))
        z.writestr('events.csv',csv_bytes(event_rows)); z.writestr('events.json',canonical(events))
        z.writestr('config.json',canonical(report['config']))
        z.writestr('README.txt','Synthetic simulation only. No credentials, raw CLI streams, reasoning, photos or database included.\n')
    return out.getvalue()

def replay(store,run,at_seq=None,internal=False):
    row=store.get(run)
    for name in ('lab/engine.py','lab/common.py'):
        if row['manifest']['source_hashes'].get(name)!=digest((ROOT/name).read_text()):
            raise ValueError('REPLAY_VERSION_MISMATCH')
    engine=Engine(row['initial']); expected_events=store.event_list(run,0,1000000)
    decisions=[e for e in expected_events if e['kind']=='DECISION']
    cursor=0; generated=[]; target=at_seq if at_seq is not None else row['state']['seq']
    while engine.s['seq']<target and not engine.complete():
        if engine.ready():
            pairs=engine.ready(); engine.events=[]
            if cursor+len(pairs)>len(decisions): break
            frozen={(w,a):engine.actions(w,a) for w,a in pairs}
            for w,a in pairs:
                event=decisions[cursor]; cursor+=1
                if (event['world_id'],event['agent_id'])!=(w,a): raise ValueError('REPLAY_ORDER')
                engine.apply(w,a,event['data'],frozen[(w,a)])
        else: engine.advance(one_event=True)
        generated.extend(engine.events)
        # A decision frontier is atomic; slider may resolve to its end.
    expected=[e for e in expected_events if e['seq']<=engine.s['seq']]
    if generated!=expected: raise ValueError('REPLAY_EVENT_MISMATCH')
    matched=engine.hash()==row['state_hash'] if engine.s['seq']==row['state']['seq'] else None
    result={'state':engine.public(),'matched_saved_state':matched,'replay_calls':0,'resolved_seq':engine.s['seq']}
    if internal: result['internal_state']=engine.s
    return result

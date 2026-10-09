import './style.css';
import {createStoreGame} from './game';
import {translate,escapeHtml as esc} from './i18n.js';

type Lang='zh'|'en';
let language:Lang=(localStorage.getItem('anywear-lab-language')==='en'?'en':'zh');
let nonce='',runId='',snapshot:any=null,report:any=null,selected={world:'control',agent:'C001'};
let agentDetail:any=null,events:any[]=[],stream:EventSource|null=null,analysisId:string|null=null;
let displayState:any=null;
let replayMode=false,replaySeq:number|null=null,runRows:any[]=[],batchRows:any[]=[],lastRefresh=0;
let stateTimer:any,rangeTimer:any,healthData:any=null;
let observedSeq:number|null=null,updateLags:number[]=[];
const t=(key:string)=>translate(language,key);
const $=<T extends HTMLElement=HTMLElement>(id:string)=>document.getElementById(id) as T;
const input=(id:string)=>$(id) as HTMLInputElement;
const value=(id:string)=>Number(input(id).value);
const money=(cents:any)=>cents===null||cents===undefined?'—':(cents/100).toLocaleString(language==='zh'?'zh-SG':'en-SG',{maximumFractionDigits:2});
const clock=(seconds:number)=>`${Math.floor(seconds/60).toString().padStart(2,'0')}:${Math.floor(seconds%60).toString().padStart(2,'0')}`;
const label=(key:string)=>`<span data-i18n="${key}">${t(key)}</span>`;
const field=(id:string,key:string,val:number,min=0,max=100000,step=1)=>`<label>${label(key)}<input id="${id}" type="number" min="${min}" max="${max}" step="${step}" value="${val}"></label>`;

$('app').innerHTML=`
<aside class="sidebar"><a class="brand" href="/lab/"><span class="brand-mark">a</span><span>anywear<span class="brand-sub">CONSUMER LAB</span></span></a>
<div class="side-heading">${label('newRun')}<span class="version">v0.1</span></div>
<div class="form-stack"><label>${label('mode')}<select id="mode"><option value="demo" data-i18n="demo">${t('demo')}</option><option value="codex" data-i18n="codex">${t('codex')}</option></select></label>
<div class="field-pair">${field('people','people',10,1,100)}${field('price','price',120,1,10000)}</div>
<p class="micro">${label('priceHint')}</p>
${field('delay','delay',0,0,60)}${field('budget','budget',200,1,100000)}${field('seed','seed',20261009,0,2147483647)}
<details><summary>${label('resources')}</summary><div class="field-pair">${field('rooms','rooms',4,1,16)}${field('devices','devices',1,1,8)}</div>
${field('noise','noise',.2,0,1,.05)}${field('arrival','arrival',30,1,600)}</details>
<button id="create" class="primary">＋ ${label('create')}</button><p class="micro">${label('noKey')}</p></div>
<div class="side-heading history-heading">${label('history')}<span id="run-count" class="version">0</span></div><div id="run-list" class="run-list"></div>
<footer class="sidebar-footer"><span class="tiny-dot"></span>${label('closedBrowser')}</footer></aside>
<main><header class="topbar"><div><div class="eyebrow">ANYWEAR / EXPERIMENT SYSTEM</div><h1>${label('title')}</h1><p>${label('subtitle')}</p></div>
<div class="top-actions"><span id="connection" class="connection">${t('connected')}</span><button id="language" class="quiet">${language==='zh'?'EN':'中文'}</button></div></header>
<div class="notice-row"><span class="pill">${label('synthetic')}</span><span id="run-status" class="status-badge">—</span><span id="run-name"></span><span id="virtual-clock" class="clock">00:00</span></div>
<div id="notice" role="status" class="notice" hidden></div>
<section id="kpis" class="kpi-grid"></section>
<div class="workspace"><section class="stage-panel"><div class="panel-heading"><div><h2 id="view-mode">${t('live')}</h2><p>${label('ordinary')}</p></div><div class="toolbar">
<button id="pause">Ⅱ ${label('pause')}</button><button id="resume">▶ ${label('resume')}</button><button id="stop" class="danger" title="${t('stopHint')}">■ ${label('stop')}</button><button id="step-event">↦ ${label('stepEvent')}</button><button id="step-decision">↪ ${label('stepDecision')}</button></div></div><p id="stop-hint" class="control-hint">${label('stopHint')}</p>
<div id="game" class="game"></div><div class="stage-tools"><div><button id="zoom-out">−</button><button id="zoom-in">＋</button><button id="reset">${label('reset')}</button><label class="check"><input id="heat" type="checkbox">${label('heat')}</label><label class="check"><input id="follow" type="checkbox">${label('follow')}</label></div>
<label class="speed">${label('speed')}<select id="speed"><option value=".5">0.5×</option><option value="1" selected>1×</option><option value="2">2×</option><option value="4">4×</option></select></label></div><p id="render-performance" class="micro control-hint"></p>
<div class="replay-bar"><span>${label('replay')}</span><input id="replay-range" type="range" min="0" max="0" value="0"><span id="replay-number">0</span><button id="back-live">${label('backLive')}</button></div>
<div class="branch-row"><button id="fork">⑂ ${label('fork')}</button><p>${label('forkHint')}</p></div></section>
<aside class="inspector"><div class="panel-heading"><h2>${label('inspector')}</h2><span id="agent-count" class="version">—</span></div>
<div class="inspector-select"><select id="agent-world"><option value="control" data-i18n="control">${t('control')}</option><option value="anywear" data-i18n="anywear">${t('anywear')}</option></select><select id="agent-select"><option>C001</option></select></div><div id="agent-detail" class="agent-detail"></div></aside></div>
<section class="bottom-panel"><nav class="tabs">${['timeline','report','debug','sensitivity'].map((k,i)=>`<button data-tab="${k}" class="${i===0?'active':''}">${label(k)}</button>`).join('')}</nav>
<div id="tab-timeline" class="tab-content"><div class="filters"><select id="world-filter"><option value="" data-i18n="all">${t('all')}</option><option value="control" data-i18n="control">${t('control')}</option><option value="anywear" data-i18n="anywear">${t('anywear')}</option></select><input id="person-filter" placeholder="${t('filterPerson')}"><select id="event-filter"><option value="" data-i18n="all">${t('all')}</option>${['DECISION','PURCHASED','LEFT','TIME_LIMIT','QUEUE_JOINED','GOAL_MET','STOCKOUT'].map(k=>`<option value="${k}" data-i18n="${k}">${t(k)}</option>`).join('')}</select><span id="event-count" class="micro"></span></div><div id="event-list" class="event-list"></div></div>
<div id="tab-report" class="tab-content" hidden><div class="report-actions"><a id="export" class="button" download>${label('export')}</a><a id="open-report" class="button" target="_blank" rel="noopener">${label('openReport')}</a><button id="verify-replay">${label('verifyReplay')}</button></div><p class="micro">${label('unit')}</p><div id="report-content"></div>
<details class="economics-editor"><summary>${label('hypothesis')}</summary><div class="economic-fields">${field('cogs','cogs',60)}${field('capex','capex',3000)}${field('fixed','fixed',200)}${field('eligible','eligible',1000,1)}${field('preview-cost','previewCost',0,0,10000,.01)}</div><h3>${label('targets')}</h3><div class="economic-fields">${field('profit-target','profitTarget',0,-1000000,1000000)}${field('leave-target','leaveTarget',0,-100,100,.1)}${field('suitable-target','suitableTarget',0,-100,100,.1)}</div><button id="analyze" class="primary">${label('analyze')}</button><p class="micro">${label('limits')}</p></details></div>
<div id="tab-debug" class="tab-content" hidden><div id="health-content"></div><div class="debug-controls"><button id="debug-refresh">${label('inspectDebug')}</button><button id="retry-unknown">${label('retryUnknown')}</button><button id="retry-failed">${label('retryFailed')}</button><button id="raise-budget">${label('raiseBudget')}</button></div><p class="micro">${label('unknownHint')}</p>
<div class="breakpoints">${label('decision')}: ${['PURCHASED','LEFT','QUEUE_JOINED','GOAL_MET'].map(k=>`<label class="check"><input type="checkbox" data-breakpoint="${k}">${label(k)}</label>`).join('')}</div><pre id="debug-state"></pre><h3>${label('issues')}</h3><div id="issues-content"></div></div>
<div id="tab-sensitivity" class="tab-content" hidden><p class="micro">${label('batchHint')}</p><div class="report-actions"><button id="plan-sensitivity">${label('planSensitivity')}</button><button id="plan-replicates">${label('planReplicates')}</button></div><div id="batches"></div></div>
</section><footer class="main-footer">${label('technical')}<span>CONCORDIA 2.4.0 · PHASER 3</span></footer></main>`;

const {scene,game}=createStoreGame($('game'),(world,agent)=>{selected={world,agent};scene.selected=world+'/'+agent;loadAgent();});
scene.language=language;

function notice(message:string,isError=false){$('notice').textContent=message;$('notice').hidden=false;$('notice').classList.toggle('error',isError);}
async function api(path:string,body?:any,retry=true):Promise<any>{
  const response=await fetch('/api/lab'+path,{method:body===undefined?'GET':'POST',headers:body===undefined?{}:{'Content-Type':'application/json','X-Lab-Nonce':nonce},body:body===undefined?undefined:JSON.stringify(body)});
  if(!response.ok){const data=await response.json().catch(()=>({error:'HTTP_'+response.status}));
    if(response.status===403&&data.error==='NONCE_REQUIRED'&&retry){nonce=(await api('/session')).nonce;return api(path,body,false);}
    throw new Error(data.error||'HTTP_'+response.status);
  }
  return response.json();
}
function action(handler:()=>Promise<any>){return async()=>{try{await handler();}catch(error){notice(t('error')+' · '+t((error as Error).message),true);}};}
function config():Record<string,any>{return {name:t('draftName'),mode:input('mode').value,n_agents:value('people'),price_cents:Math.round(value('price')*100),
  initial_fitting_delay:Math.round(value('delay')*60),attempt_budget:value('budget'),seed:value('seed'),
  fitting_rooms:value('rooms'),preview_devices:value('devices'),preview_noise:value('noise'),arrival_seconds:value('arrival')};}
function applyForm(c:any){for(const [id,key,scale] of [['people','n_agents',1],['price','price_cents',.01],['delay','initial_fitting_delay',1/60],
 ['budget','attempt_budget',1],['seed','seed',1],['rooms','fitting_rooms',1],['devices','preview_devices',1],['noise','preview_noise',1],['arrival','arrival_seconds',1]] as any[]){input(id).value=String(c[key]*scale);}input('mode').value=c.mode;}
async function refreshRuns(){runRows=await api('/runs');renderRuns();}
function renderRuns(){
  $('run-count').textContent=String(runRows.length);
  $('run-list').innerHTML=runRows.length?runRows.map(r=>`<button class="run-item ${r.id===runId?'selected':''}" data-run="${r.id}"><span class="run-title">${esc(r.config.name)}</span><span class="run-meta">${r.config.n_agents} × 2 · ${r.config.mode==='demo'?'DEMO':'CODEX'} <i>${esc(t(r.status))}</i></span></button>`).join(''):`<p class="micro">${t('emptyRuns')}</p>`;
  document.querySelectorAll<HTMLElement>('[data-run]').forEach(el=>el.onclick=action(()=>selectRun(el.dataset.run!)));
}
async function selectRun(id:string){
  $('notice').hidden=true;stream?.close();runId=id;analysisId=null;replayMode=false;replaySeq=null;events=[];agentDetail=null;
  observedSeq=null;updateLags=[];
  const row=runRows.find(r=>r.id===id);if(row)applyForm(row.config);
  $('export').setAttribute('href',`/api/lab/runs/${id}/export`);$('open-report').setAttribute('href',`/api/lab/runs/${id}/report.html`);
  await refreshState();await refreshReport();
  const currentSeq=snapshot?.state.seq||0;events=await api(`/runs/${runId}/events?after=${Math.max(0,currentSeq-200)}&limit=300`);renderEvents();
  stream=new EventSource(`/api/lab/runs/${id}/stream?after=${currentSeq}`);
  stream.addEventListener('world',event=>{const item=JSON.parse((event as MessageEvent).data);if(item.run_id!==runId)return;
    if(!events.some(e=>e.seq===item.seq))events.push(item);events=events.slice(-1000);renderEvents();scheduleState();});
  stream.addEventListener('heartbeat',()=>scheduleState());
  stream.onopen=()=>{$('connection').textContent=t('connected');$('connection').classList.remove('offline');};
  stream.onerror=()=>{$('connection').textContent=t('disconnected');$('connection').classList.add('offline');};
  renderRuns();
}
function scheduleState(){clearTimeout(stateTimer);stateTimer=setTimeout(()=>refreshState().catch(()=>{}),200);}
async function refreshState(){
  if(!runId)return;const id=runId;const data=await api(`/runs/${id}/state`);if(id!==runId)return;
  if(observedSeq!==null&&data.state.seq>observedSeq&&Number.isFinite(data.updated_wall_ms))updateLags.push(Math.max(0,Date.now()-data.updated_wall_ms));
  updateLags=updateLags.slice(-100);observedSeq=data.state.seq;snapshot=data;lastRefresh=performance.now();
  $('run-status').textContent=t(data.status);$('run-status').className='status-badge '+data.status.toLowerCase();
  $('run-name').textContent=data.state.config.name+(data.parent?' · ⑂':'');
  if(data.error)notice(t(data.error),true);
  const range=input('replay-range');range.max=String(data.state.seq);range.min=String(data.parent_seq||0);
  if(!replayMode){range.value=String(data.state.seq);$('replay-number').textContent=String(data.state.seq);renderWorld(data.state);}
  $('pause').toggleAttribute('disabled',data.status!=='RUNNING');
  const ended=['COMPLETED','STOPPING','STOPPED','INCOMPLETE'].includes(data.status);
  $('resume').toggleAttribute('disabled',ended||['RUNNING','PAUSING'].includes(data.status));
  $('stop').toggleAttribute('disabled',ended);
  $('fork').toggleAttribute('disabled',['RUNNING','PAUSING','STOPPING'].includes(data.status));
  for(const id of ['step-event','step-decision'])$(id).toggleAttribute('disabled',ended||['RUNNING','PAUSING'].includes(data.status));
  document.querySelectorAll<HTMLInputElement>('[data-breakpoint]').forEach(el=>el.checked=data.controls.breakpoints.includes(el.dataset.breakpoint));
  if(!replayMode)await loadAgent();
}
function renderWorld(state:any){
  displayState=state;scene.renderState(state);$('virtual-clock').textContent=clock(state.t);$('view-mode').textContent=t(replayMode?'replay':'live');
  const agentSelect=$('agent-select') as HTMLSelectElement;const old=selected.agent;
  if(agentSelect.options.length!==Object.keys(state.personas).length)agentSelect.innerHTML=Object.keys(state.personas).map(id=>`<option value="${id}">${id}</option>`).join('');
  if(!state.personas[old])selected.agent=Object.keys(state.personas)[0];agentSelect.value=selected.agent;
  input('agent-world').value=selected.world;$('agent-count').textContent=String(Object.keys(state.personas).length);
  if(replayMode){agentDetail={consumer:state.worlds[selected.world].agents[selected.agent],visible_observation:{persona:state.personas[selected.agent],allowed_actions:[]}};renderAgent();}
}
async function refreshReport(){if(!runId)return;const id=runId;const data=await api(`/runs/${id}/report${analysisId?'?analysis_id='+analysisId:''}`);if(id!==runId)return;report=data;renderKpis();renderReport();}
function renderKpis(){
  const a=report?.worlds.control,b=report?.worlds.anywear;
  const items=[['entered',a?`${a.entered} / ${a.planned} · ${b.entered} / ${b.planned}`:'—','A · B'],
    ['purchase',a?`${a.paid} → ${b.paid}`:'—',a?`${(a.purchase_rate*100).toFixed(1)}% → ${(b.purchase_rate*100).toFixed(1)}%`:'—'],
    ['leave',a?`${a.left+a.time_limit} → ${b.left+b.time_limit}`:'—',a?`${a.censored+b.censored} ${t('censored')}`:'—'],
    ['suitable',a?`${a.suitable} → ${b.suitable}`:'—',t('goal')],
    ['waiting',a?`${a.wait_p95_seconds??'—'} → ${b.wait_p95_seconds??'—'}`:'—',t('seconds')],
    ['calls',report?`${report.usage.cli_attempts} / ${report.usage.budget_cli_attempts}`:'—',report?`${t('tokens')}: ${report.usage.input_tokens===null||report.usage.output_tokens===null?t('unknown'):(report.usage.input_tokens+report.usage.output_tokens).toLocaleString()}`:'—']];
  $('kpis').innerHTML=items.map(([key,v,sub])=>`<article class="kpi"><span>${t(key)}</span><strong>${esc(v)}</strong><small>${esc(sub)}</small></article>`).join('');
}
async function loadAgent(){
  if(!runId||!snapshot)return;if(replayMode){renderWorld(displayState);return;}
  const id=runId,w=selected.world,a=selected.agent;
  const detail=await api(`/runs/${id}/agents/${w}/${a}`);if(id!==runId||w!==selected.world||a!==selected.agent)return;
  agentDetail=detail;scene.selected=w+'/'+a;renderAgent();
}
function renderAgent(){
  if(!agentDetail){$('agent-detail').innerHTML=`<p class="micro">${t('selectPerson')}</p>`;return;}
  const a=agentDetail.consumer,o=agentDetail.visible_observation,p=o.persona;
  const reason=a.last_decision?.[language==='zh'?'reason_zh':'reason_en'];
  const memoryOpen=$('all-memory')?.hasAttribute('open');
  $('agent-detail').innerHTML=`<div class="person-heading"><span class="person-avatar">${a.id.slice(1)}</span><div><h3>${a.id}</h3><span class="mini-status">${t(a.status)}</span></div></div>
  <p class="micro">${t('given')}</p><dl class="traits"><dt>${t('personaBudget')}</dt><dd>SGD ${money(p.budget_cents)}</dd><dt>${t('remaining')}</dt><dd>${clock(o.remaining_seconds??Math.max(0,a.deadline-(a.ended_at??displayState?.t??0)))}</dd>
  <dt>${t('stylePreference')}</dt><dd>${p.style_preference.toFixed(2)}</dd><dt>${t('patience')}</dt><dd>${clock(p.patience_seconds)}</dd>
  <dt>${t('privacy')}</dt><dd>${p.privacy.toFixed(2)}</dd><dt>${t('trust')}</dt><dd>${p.trust.toFixed(2)}</dd><dt>${t('accept')}</dt><dd>${p.accept_threshold.toFixed(2)}</dd><dt>${t('goal')}</dt><dd>${a.suitable?'✓':a.ended_at!==null?'—':t('pending')}</dd></dl><p class="micro">${t('personaHint')}</p>
  <h4>${t('decision')}</h4><div class="decision-card"><strong>${a.last_decision?esc(t(a.last_decision.action==='leave'?'leaveAction':a.last_decision.action)+' '+a.last_decision.sku):'—'}</strong><p>${esc(reason||t('waitingModel'))}</p><small>${t('reason')}</small></div>
  <h4>${t('knownProducts')}</h4><div class="known-products">${Object.entries(a.known||{}).map(([sku,raw])=>{const k:any=raw;return `<div><strong>${esc(sku)}</strong><p>${[['fit',k.fit],['appearance',k.appearance],['previewSignal',k.preview]].filter(([,v])=>typeof v==='number').map(([key,v])=>`${t(String(key))}: ${Number(v).toFixed(2)}`).join(' · ')||t('metadataOnly')}</p></div>`;}).join('')||`<p class="micro">${t('noKnownProducts')}</p>`}</div>
  <h4>${t('memory')} <span>${a.memory.length}</span></h4><p class="micro">${t('memoryHint')}</p><div class="memories">${a.memory.slice(-7).reverse().map((m:any)=>`<div><time>${clock(m.time)}</time><span>${esc(t(m.kind))}${m.data.sku?' · '+esc(m.data.sku):''}${m.data[language==='zh'?'reason_zh':'reason_en']?`<small>${esc(m.data[language==='zh'?'reason_zh':'reason_en'])}</small>`:''}</span></div>`).join('')}</div>
  <details id="all-memory" ${memoryOpen?'open':''}><summary>${t('allMemory')} (${a.memory.length})</summary><pre class="memory-json">${esc(JSON.stringify(a.memory,null,2))}</pre></details>
  <details><summary>${t('options')}</summary><select id="manual-choice">${(o.allowed_actions||[]).map((v:any)=>`<option value="${esc(JSON.stringify(v))}">${esc(t(v.action==='leave'?'leaveAction':v.action)+' '+v.sku)}</option>`).join('')}</select><button id="manual" ${(!a.ready||replayMode||snapshot?.status!=='PAUSED')?'disabled':''}>${t('manual')}</button><p class="micro">${t('manualHint')}</p></details>`;
  $('manual').onclick=action(async()=>{const choice=JSON.parse(input('manual-choice').value);const child=await api(`/runs/${runId}/fork`,{expected_hash:snapshot.state.state_hash,world:selected.world,agent:selected.agent,
    decision:{...choice,reason_code:'no_options',reason_zh:'观察者手动干预。',reason_en:'Manual observer intervention.'}});await refreshRuns();await selectRun(child.run_id);});
}
function renderEvents(){
  const wf=input('world-filter').value,pf=input('person-filter').value.trim().toUpperCase(),ef=input('event-filter').value;
  const filtered=events.filter(e=>(!wf||e.world_id===wf)&&(!pf||(e.agent_id||'').includes(pf))&&(!ef||e.kind===ef));
  $('event-count').textContent=String(filtered.length);
  $('event-list').innerHTML=filtered.length?filtered.slice(-150).reverse().map(e=>`<button class="event-row ${['PURCHASED','LEFT','GOAL_MET','STOCKOUT'].includes(e.kind)?'key-event':''}" data-seq="${e.seq}"><span class="event-time">${clock(e.virtual_time)}</span><span class="world-tag ${e.world_id}">${e.world_id==='control'?'A':'B'}</span><b>${esc(e.agent_id||'—')}</b><span>${esc(t(e.kind))}</span><small>${esc(e.kind==='DECISION'?(e.data[language==='zh'?'reason_zh':'reason_en']||''):(e.data.sku||''))}</small><i>#${e.seq}</i></button>`).join(''):`<p class="empty">${t('noEvents')}</p>`;
  document.querySelectorAll<HTMLElement>('[data-seq]').forEach(el=>el.onclick=action(()=>showReplay(Number(el.dataset.seq))));
}
function renderReport(){
  if(!report){$('report-content').innerHTML=t('reportEmpty');return;}
  const a=report.worlds.control,b=report.worlds.anywear,e=report.economics;
  const rows=[['planned','planned'],['terminal','natural_terminal'],['pending','pending'],['censored','censored'],['purchase','paid'],['LEFT','left'],['TIME_LIMIT','time_limit'],['suitable','suitable'],['waitP50','wait_p50_seconds'],['waitP95','wait_p95_seconds'],['openQueue','open_wait_episodes'],['revenue','revenue_cents'],['contribution','contribution_cents']];
  $('report-content').innerHTML=`<div class="report-status"><span class="status-badge ${report.complete?'completed':'paused'}">${t(report.complete?'complete':'incomplete')}</span><strong>${esc(t(report.goals.status))}</strong><small>${t(report.exploratory?'exploratory':'robustness')}</small>${report.goals.post_hoc?`<em>${t('postHoc')}</em>`:''}</div>
  <div class="report-columns"><table><thead><tr><th></th><th>A · ${t('control')}</th><th>B · ${t('anywear')}</th></tr></thead><tbody>${rows.map(([label,key])=>`<tr><td>${t(label)}</td><td>${key.endsWith('cents')?money(a[key]):a[key]??'—'}</td><td>${key.endsWith('cents')?money(b[key]):b[key]??'—'}</td></tr>`).join('')}</tbody></table>
  <div class="economic-summary"><h3>${t('hypothesis')}</h3><dl><dt>${t('monthly')}</dt><dd>${money(e.monthly_increment_cents)}</dd><dt>${t('payback')}</dt><dd>${e.payback_months??'—'}</dd><dt>${t('roi')}</dt><dd>${e.roi_12_months===null?'—':(e.roi_12_months*100).toFixed(1)+'%'}</dd></dl><p class="micro">${t('limits')}</p><h4>${t('utilization')}</h4>${['fitting','preview','checkout'].map(r=>`<div class="util-row"><span>${t(r)}</span><i style="--a:${a.resources[r].consumer_fraction*100}%;--b:${b.resources[r].consumer_fraction*100}%"></i><small>${(a.resources[r].consumer_fraction*100).toFixed(0)} / ${(b.resources[r].consumer_fraction*100).toFixed(0)}%</small></div>`).join('')}</div></div>`;
}
async function refreshHealth(){healthData=await api('/health');renderHealth();}
function renderHealth(){if(!healthData)return;const h=healthData;
  $('health-content').innerHTML=`<div class="health-grid">${['api','worker'].map(k=>`<article><span>${t(k)}</span><b class="${(h.services[k]?.age_seconds<15&&!h.services[k]?.value.stopped)?'good':'bad'}">${(h.services[k]?.age_seconds<15&&!h.services[k]?.value.stopped)?t('connected'):t('disconnected')}</b><small>${h.services[k]?.age_seconds??'—'} s</small></article>`).join('')}
  <article><span>${t('gate')}</span><b class="${h.isolation_gate.passed?'good':'bad'}">${t(h.isolation_gate.passed?'passed':'needsProbe')}</b><small>gpt-6.1-sol</small></article><article><span>${t('disk')}</span><b>${(h.disk_free_bytes/1e9).toFixed(1)} GB</b><small>localhost</small></article></div>`;
  const option=document.querySelector<HTMLOptionElement>('#mode option[value="codex"]');if(option)option.disabled=!h.isolation_gate.passed;
}
async function debugRefresh(){if(!runId)return;const data=await api(`/runs/${runId}/debug`);$('debug-state').textContent=JSON.stringify(data,null,2);
  $('issues-content').innerHTML=data.issues.length?data.issues.map((i:any)=>`<div class="issue"><b>${esc(i.severity+' · '+i.code)}</b><small>${esc(i.id)}</small><p>${esc(i.detail)}</p></div>`).join(''):`<p class="micro">${t('noIssues')}</p>`;}
async function showReplay(seq:number){if(!runId)return;const data=await api(`/runs/${runId}/replay?seq=${seq}`);replayMode=true;replaySeq=data.resolved_seq;input('replay-range').value=String(replaySeq);$('replay-number').textContent=String(replaySeq);renderWorld(data.state);}
async function command(command:string){if(!runId)return;await api(`/runs/${runId}/control`,{command});await refreshState();await refreshRuns();if(command==='stop'){await refreshReport();notice(t('stopHint'));}}
async function refreshBatches(){batchRows=await api('/batches');renderBatches();}
function renderBatches(){
  $('batches').innerHTML=batchRows.length?batchRows.map(b=>`<article class="batch"><div class="batch-heading"><h3>${b.kind==='sensitivity'?t('sensitivity'):t('ci')}</h3><span>${t('maxAttempts')}: ${b.maximum_cli_attempts}</span>${b.cells.every((c:any)=>!c.run_id)?`<button data-start-batch="${b.id}" class="primary">${t('startBatch')}</button>`:''}</div><div class="matrix">${b.cells.map((c:any)=>`<button ${c.run_id?`data-cell-run="${c.run_id}"`:''}><strong>${c.price_cents?'SGD '+c.price_cents/100+' · '+c.initial_fitting_delay/60+' min':'seed '+c.seed}</strong><span>${esc(t(c.status==='NOT_RUN'?'notRun':c.status))}</span><small>${c.purchase_delta===undefined?'—':'Δ '+(c.purchase_delta*100).toFixed(1)+' pp'}</small></button>`).join('')}</div></article>`).join(''):`<p class="empty">${t('noBatch')}</p>`;
  document.querySelectorAll<HTMLElement>('[data-start-batch]').forEach(el=>el.onclick=action(async()=>{await api(`/batches/${el.dataset.startBatch}/start`,{});await refreshRuns();await refreshBatches();}));
  document.querySelectorAll<HTMLElement>('[data-cell-run]').forEach(el=>el.onclick=action(()=>selectRun(el.dataset.cellRun!)));
}

$('create').onclick=action(async()=>{const result=await api('/runs',config());await api(`/runs/${result.run_id}/control`,{command:'start'});await refreshRuns();await selectRun(result.run_id);});
input('people').onchange=()=>input('budget').value=String(value('people')*20);
for(const [id,cmd] of [['pause','pause'],['resume','resume'],['step-event','step_event'],['step-decision','step_decision'],['stop','stop'],['retry-unknown','resubmit_unknown'],['retry-failed','retry_failed']])$(id).onclick=action(()=>command(cmd));
$('raise-budget').onclick=action(async()=>{await api(`/runs/${runId}/control`,{command:'budget',budget:value('budget')});await refreshState();await refreshReport();});
$('fork').onclick=action(async()=>{const c=config();for(const key of ['n_agents','seed','initial_fitting_delay','mode'])if(c[key]!==snapshot.state.config[key])throw new Error('INITIAL_CONDITION_REQUIRES_NEW_RUN');const patch:any={};for(const key of ['price_cents','stock_per_sku','arrival_seconds','fitting_rooms','preview_devices','preview_noise'])if(c[key]!==undefined&&c[key]!==snapshot.state.config[key])patch[key]=c[key];
  const child=await api(`/runs/${runId}/fork`,{expected_hash:snapshot.state.state_hash,patch,at_seq:replayMode?replaySeq:null});await refreshRuns();await selectRun(child.run_id);});
$('zoom-in').onclick=()=>scene.zoom(.25);$('zoom-out').onclick=()=>scene.zoom(-.25);$('reset').onclick=()=>{scene.reset();input('follow').checked=false;};
input('heat').onchange=()=>{scene.showHeat=input('heat').checked;if(scene.state)scene.renderState(scene.state);};
input('follow').onchange=()=>scene.follow=input('follow').checked;input('speed').onchange=()=>scene.speed=value('speed');
for(const id of ['agent-world','agent-select'])input(id).onchange=()=>{selected={world:input('agent-world').value,agent:input('agent-select').value};loadAgent().catch(()=>{});};
for(const id of ['world-filter','person-filter','event-filter'])input(id).oninput=renderEvents;
input('replay-range').oninput=()=>{clearTimeout(rangeTimer);rangeTimer=setTimeout(()=>showReplay(value('replay-range')).catch(()=>{}),250);};
$('back-live').onclick=()=>{replayMode=false;replaySeq=null;refreshState().catch(()=>{});};
$('verify-replay').onclick=action(async()=>{const result=await api(`/runs/${runId}/replay`);notice(result.matched_saved_state?t('replayVerified'):'REPLAY_STATE_MISMATCH',!result.matched_saved_state);});
$('debug-refresh').onclick=action(debugRefresh);
document.querySelectorAll<HTMLInputElement>('[data-breakpoint]').forEach(el=>el.onchange=action(async()=>{await api(`/runs/${runId}/control`,{command:'breakpoints',breakpoints:[...document.querySelectorAll<HTMLInputElement>('[data-breakpoint]:checked')].map(e=>e.dataset.breakpoint)});}));
$('analyze').onclick=action(async()=>{const result=await api(`/runs/${runId}/analyses`,{costs:{cogs_cents:Math.round(value('cogs')*100),capex_cents:Math.round(value('capex')*100),monthly_fixed_cents:Math.round(value('fixed')*100),monthly_eligible:value('eligible'),preview_cents:Math.round(value('preview-cost')*100),assumed:true},targets:{min_monthly_increment_cents:Math.round(value('profit-target')*100),max_leave_delta:value('leave-target')/100,min_suitable_delta:value('suitable-target')/100}});analysisId=result.analysis_id;report=result.report;renderReport();notice(report.goals.post_hoc?t('postHoc'):t('analyze'));});
for(const [id,kind] of [['plan-sensitivity','sensitivity'],['plan-replicates','replicates']])$(id).onclick=action(async()=>{await api('/batches',{kind,config:config()});await refreshBatches();});
document.querySelectorAll<HTMLElement>('[data-tab]').forEach(button=>button.onclick=()=>{document.querySelectorAll('[data-tab]').forEach(b=>b.classList.remove('active'));button.classList.add('active');for(const key of ['timeline','report','debug','sensitivity'])$('tab-'+key).hidden=key!==button.dataset.tab;if(button.dataset.tab==='debug')debugRefresh().catch(()=>{});if(button.dataset.tab==='sensitivity')refreshBatches().catch(()=>{});});
$('language').onclick=()=>{language=language==='zh'?'en':'zh';localStorage.setItem('anywear-lab-language',language);document.documentElement.lang=language==='zh'?'zh-CN':'en';
  $('stop').title=t('stopHint');
  document.querySelectorAll<HTMLElement>('[data-i18n]').forEach(el=>el.textContent=t(el.dataset.i18n!));$('language').textContent=language==='zh'?'EN':'中文';input('person-filter').placeholder=t('filterPerson');
  $('view-mode').textContent=t(replayMode?'replay':'live');$('connection').textContent=t($('connection').classList.contains('offline')?'disconnected':'connected');scene.setLanguage(language);renderRuns();renderKpis();renderAgent();renderEvents();renderReport();renderHealth();renderBatches();if(snapshot)$('run-status').textContent=t(snapshot.status);};

async function boot(){nonce=(await api('/session')).nonce;await refreshHealth();await refreshRuns();renderKpis();renderAgent();renderReport();if(runRows.length)await selectRun(runRows[0].id);}
boot().catch(error=>notice(t('error')+' · '+t(error.message),true));
setInterval(()=>{if(runId)refreshReport().catch(()=>{});},2500);
setInterval(()=>{refreshHealth().catch(()=>{});refreshRuns().catch(()=>{});},5000);
setInterval(()=>{const sorted=[...updateLags].sort((a,b)=>a-b),p95=sorted.length?sorted[Math.ceil(sorted.length*.95)-1]:null;
  $('render-performance').textContent=`${t('renderFps')}: ${Math.round(game.loop.actualFps)} fps · ${t('updateLag')}: ${p95??'—'} ms (n=${sorted.length})`;
  $('render-performance').dataset.fps=String(game.loop.actualFps);$('render-performance').dataset.updateP95=String(p95??'');
},1000);
// Read-only instrumentation for acceptance; contains no auth or prompts.
(window as any).__anywearLab={get fps(){return game.loop.actualFps;},get run(){return runId;},get lastRefresh(){return lastRefresh;},get replay(){return replayMode;}};

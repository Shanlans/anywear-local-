import {RATE,estimateSession,summarize} from './billing-model.js';
const KEY='anywear-billing-v1';let saved;try{saved=JSON.parse(localStorage.getItem(KEY)||'{}');}catch{saved={};}
let history=Array.isArray(saved.history)?saved.history:[],snapshot=saved.snapshot||null,active=null;
// A tab crash cannot establish the actual stop time at Decart; keep an explicitly incomplete record.
if(saved.active){const entry=saved.active;entry.endedAt=entry.lastSeenAt||Date.now();entry.generatingAt=null;entry.status='中断待核对';history.push(entry);}
const $=id=>document.getElementById(id),money=n=>n==null?'—':new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:4,maximumFractionDigits:4}).format(n);
function persist(){try{localStorage.setItem(KEY,JSON.stringify({history,snapshot,active}));}catch{$('billingNotice').textContent='无法保存记录，请检查浏览器本地存储。';}}
function writeCell(row,value){const td=document.createElement('td');td.textContent=value;row.append(td);}
function render(){
 const stats=summarize(history),live=active?estimateSession(active):null;
 $('liveCost').textContent=live?money(live.cost):'$0.0000';$('liveDuration').textContent=live?Math.floor(live.elapsed)+' s':'0 s';
 $('totalCost').textContent=money(stats.total+(live?.cost||0));$('averageCost').textContent=money(stats.average);
 $('sessionCount').textContent=String(stats.count);$('unknownCount').textContent=stats.unknown?`未确认记录 ${stats.unknown}`:'';
 const after=snapshot?Math.max(0,stats.total-snapshot.totalAtSnapshot)+(live?.cost||0):null;
 $('remainingCost').textContent=snapshot?money(snapshot.amount-after):'—';
 $('balanceStatus').textContent=snapshot?'手动余额扣减本地估算':'真实账户余额未读取';
 const dateLocale=document.documentElement.lang==='en'?'en-SG':'zh-CN';
 $('balanceTime').textContent=snapshot?new Date(snapshot.at).toLocaleString(dateLocale,{timeZone:'Asia/Singapore'}):'';
 $('billingRows').replaceChildren(...history.slice().reverse().map(s=>{const row=document.createElement('tr'),v=estimateSession(s,s.endedAt);writeCell(row,new Date(s.startedAt).toLocaleString(dateLocale,{timeZone:'Asia/Singapore'}));writeCell(row,Math.round(v.elapsed)+' s');writeCell(row,v.cost==null?'—':v.seconds.toFixed(1)+' s');writeCell(row,money(v.cost));writeCell(row,s.status);writeCell(row,v.cost==null?'未确认生成':v.basis==='reported'?'SDK 回报时长估算':'本地生成时长估算');return row;}));
 $('billingEmpty').hidden=history.length>0;$('saveBalance').disabled=!!active;$('clearBalance').disabled=!!active;
 if(active){active.lastSeenAt=Date.now();persist();}
}
export function mountBilling(){
 const panel=document.createElement('section');panel.className='billing-panel';panel.innerHTML=`<div class="eyebrow">USAGE / USD</div><h2>试衣花费，一目了然。</h2><p class="billing-description">按标准 VTON $0.02/生成秒估算，约 $1.20/分钟；仅供预算，非官方账单。</p><div class="billing-grid"><div><small>本次估算</small><strong id="liveCost">$0.0000</strong><span id="liveDuration">0 s</span></div><div><small>累计估算</small><strong id="totalCost">$0.0000</strong><span id="unknownCount"></span></div><div><small>平均每次</small><strong id="averageCost">—</strong><span>仅含可估算的已结束会话</span></div><div><small>已结束次数</small><strong id="sessionCount">0</strong><span>从开始点击至结束记录</span></div><div><small>剩余金额估算</small><strong id="remainingCost">—</strong><span id="balanceStatus">真实账户余额未读取</span></div></div><div class="balance-controls"><label>平台当前余额 USD <input id="balanceInput" type="number" min="0" max="1000000" step="0.01" placeholder="手动填写"></label><button id="saveBalance" class="secondary">校准余额</button><button id="clearBalance" class="secondary">清除校准</button><a href="https://platform.decart.ai" target="_blank" rel="noreferrer">查看官方账户 ↗</a><span id="balanceTime"></span></div><p id="billingNotice" class="billing-description">公开 API 未查到金额余额查询接口。手动余额只扣减校准后本页面估算，不含其他应用、其他浏览器或平台调整；校准时请先结束会话。</p><div class="billing-table-wrap"><table><thead><tr><th>开始时间</th><th>点击到结束</th><th>估算生成时长</th><th>估算花费</th><th>结果</th><th>统计依据</th></tr></thead><tbody id="billingRows"></tbody></table><p id="billingEmpty">开始一次实时试衣后，记录会出现在这里。</p></div><p class="billing-description">记录保存在此浏览器本机。预览与检查 API 不计入试衣次数；未确认生成的失败记录显示 —。SDK 时长仍不等于平台结算金额。页面异常中断需到平台核对。</p>`;
 document.querySelector('main').after(panel);
 $('saveBalance').onclick=()=>{const n=Number($('balanceInput').value);if(active||!$('balanceInput').value||!Number.isFinite(n)||n<0||n>1000000)return;snapshot={amount:n,totalAtSnapshot:summarize(history).total,at:Date.now()};persist();render();};
 $('clearBalance').onclick=()=>{if(active)return;snapshot=null;$('balanceInput').value='';persist();render();};
 setInterval(render,1000);render();
}
export const billing={
 begin(model){if(active)return;active={id:crypto.randomUUID(),model,rate:RATE,startedAt:Date.now(),observedMs:0,generatingAt:null,sawGeneration:false,hasReported:false,reportedSeconds:0,lastTick:0,status:'进行中'};persist();render();},
 state(state){if(!active)return;if(state==='generating'){if(active.generatingAt==null)active.generatingAt=Date.now();active.sawGeneration=true;}
 else if(['disconnected','reconnecting','connected'].includes(state)){if(active.generatingAt!=null){active.observedMs+=Date.now()-active.generatingAt;active.generatingAt=null;}if(state==='reconnecting')active.lastTick=0;}render();},
 report(seconds){if(!active||!Number.isFinite(seconds)||seconds<0)return;active.hasReported=true;active.sawGeneration=true;active.reportedSeconds+=Math.max(0,seconds-active.lastTick);active.lastTick=Math.max(active.lastTick,seconds);render();},
 end(status='已结束'){if(!active)return;const now=Date.now();if(active.generatingAt!=null)active.observedMs+=now-active.generatingAt;active.generatingAt=null;active.endedAt=now;active.status=status;history.push(active);active=null;persist();render();}
};

import test from 'node:test';
import assert from 'node:assert/strict';
import {SessionDeadline,sessionLimit} from '../src/session-deadline.js';
import {SessionLane} from '../src/session-model.js';
function clock(){let now=0,id=0;const timers=new Map();return {now:()=>now,schedule(fn,delay){timers.set(++id,{fn,at:now+delay});return id;},cancel(id){timers.delete(id);},advance(ms){const end=now+ms;while(true){const next=[...timers].filter(([,t])=>t.at<=end).sort((a,b)=>a[1].at-b[1].at)[0];if(!next)break;timers.delete(next[0]);now=next[1].at;next[1].fn();}now=end;}};}
test('session limits default to 30 seconds and cannot be raised by stale configuration',()=>{
 for(const value of [undefined,NaN,'invalid',0,-5,Infinity,300,'1800'])assert.equal(sessionLimit(value),30);
 assert.equal(sessionLimit('30'),30);assert.equal(sessionLimit(20.9),20);assert.equal(sessionLimit(1),10);
});
test('deadline warns at 25s and disconnects a live session at 30s including connection time',()=>{
 const time=clock(),deadline=new SessionDeadline(time),lane=new SessionLane(),run=lane.begin();let warnings=0,disconnects=0;
 deadline.start({seconds:30,current:()=>lane.current(run),onWarn:()=>warnings++,onExpire:()=>lane.cancel()});
 time.advance(4000);lane.resolve(run,{disconnect(){disconnects++;}});
 time.advance(20999);assert.equal(warnings,0);assert.equal(deadline.remaining,6);
 time.advance(1);assert.equal(warnings,1);time.advance(4999);assert.equal(disconnects,0);
 time.advance(1);assert.equal(disconnects,1);assert.equal(lane.connection,null);assert.equal(deadline.remaining,null);
});
test('deadline cancels a pending dial and immediately disconnects its late handle',()=>{
 const time=clock(),deadline=new SessionDeadline(time),lane=new SessionLane(),run=lane.begin();let disconnects=0;
 deadline.start({seconds:30,current:()=>lane.current(run),onWarn(){},onExpire:()=>lane.cancel()});time.advance(30000);
 assert.equal(lane.pending,true);assert.throws(()=>lane.begin(),/SESSION_BUSY/);
 assert.equal(lane.resolve(run,{disconnect(){disconnects++;}}),false);assert.equal(disconnects,1);assert.equal(lane.connection,null);
});
test('manual clear and a new deadline prevent a stale timer from stopping the next session',()=>{
 const time=clock(),deadline=new SessionDeadline(time);let stops=0,warnings=0;
 const options={seconds:30,current:()=>true,onWarn:()=>warnings++,onExpire:()=>stops++};
 deadline.start(options);time.advance(10000);deadline.clear();time.advance(20000);assert.equal(stops,0);assert.equal(warnings,0);
 deadline.start(options);time.advance(30000);assert.equal(stops,1);assert.equal(warnings,1);
});
test('default browser timer calls preserve the global receiver',()=>{
 const savedSet=globalThis.setTimeout,savedClear=globalThis.clearTimeout,calls=[];let id=0;
 try{
  globalThis.setTimeout=function(fn,delay){assert.equal(this,globalThis);calls.push(delay);return ++id;};
  globalThis.clearTimeout=function(timer){assert.equal(this,globalThis);calls.push('clear:'+timer);};
  const deadline=new SessionDeadline();deadline.start({seconds:30,current:()=>true,onWarn(){},onExpire(){}});deadline.clear();
  assert.deepEqual(calls,[25000,30000,'clear:1','clear:2']);
 }finally{globalThis.setTimeout=savedSet;globalThis.clearTimeout=savedClear;}
});

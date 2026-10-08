import {test} from 'node:test';
import assert from 'node:assert/strict';
import {estimateSession,summarize} from '../src/billing-model.js';
test('charge estimate excludes permission wait and uses SDK generation seconds',()=>{
 const s={startedAt:0,endedAt:90000,sawGeneration:true,hasReported:true,reportedSeconds:30,observedMs:32000,rate:.02};
 const v=estimateSession(s);assert.equal(v.elapsed,90);assert.equal(v.seconds,30);assert.equal(v.cost,.6);
});
test('an unconfirmed failed connection is unknown, not zero charge',()=>{assert.equal(estimateSession({startedAt:0,endedAt:4000,sawGeneration:false}).cost,null);});
test('local estimate counts only observed generation and completed averages exclude unknown records',()=>{
 const a={startedAt:0,endedAt:60000,sawGeneration:true,observedMs:20000};
 const b={startedAt:0,endedAt:4000,sawGeneration:false};
 assert.equal(estimateSession(a).cost,.4);assert.deepEqual(summarize([a,b]),{total:.4,average:.4,count:2,priced:1,unknown:1});
});
test('live generation updates without charging the entire start-to-end interval',()=>{
 const v=estimateSession({startedAt:1000,generatingAt:10000,observedMs:2000,sawGeneration:true},13000);assert.equal(v.elapsed,12);assert.equal(v.seconds,5);assert.equal(v.cost,.1);
});

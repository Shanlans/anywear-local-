import {test} from 'node:test';
import assert from 'node:assert/strict';
import {apiFailureHint,sessionEndInfo,scheduleDisconnected} from '../src/connection-notices.js';
test('generic WebRTC server errors retain credit/auth hints without displaying raw account data',()=>{
 assert.equal(apiFailureHint({code:'WEBRTC_SERVER_ERROR',message:'Insufficient credits for session'}),'Decart 额度或并发不足，请检查账户。');
 assert.equal(apiFailureHint({code:'INSUFFICIENT_CREDITS'}),'Decart 额度或并发不足，请检查账户。');
 assert.equal(apiFailureHint({code:'INVALID_API_KEY',message:'Rejected credential'}),'Decart 身份验证失败，请检查密钥和权限。');
 assert.equal(apiFailureHint({code:'INVALID_INPUT',message:'Prompt too long'}),null);
 assert.equal(apiFailureHint(Error('network unavailable')),null);
});
test('structured termination separates insufficient credits from concurrency and masks unknown reasons',()=>{
 const credits=sessionEndInfo('insufficient_credits'),concurrency=sessionEndInfo('session_limit');
 assert.equal(credits.code,'SESSION_END_INSUFFICIENT_CREDITS');assert.equal(concurrency.code,'SESSION_END_CONCURRENCY_LIMIT');assert.notEqual(credits.message,concurrency.message);assert.equal(credits.error,true);
 assert.equal(sessionEndInfo('policy_violation').code,'SESSION_END_POLICY');
 const unknown=sessionEndInfo('https://example.test/private-reason');assert.equal(unknown.code,'SESSION_END_UNKNOWN');assert.equal(unknown.message.includes('private'),false);assert.equal(unknown.error,false);
});
test('terminal session reason wins SDK disconnected ordering; cancelled runs and pending dials cannot be stopped late',()=>{
 let current=true,pending=false,hint=null;const jobs=[],calls=[];
 const schedule=()=>scheduleDisconnected({current:()=>current,pending:()=>pending,message:()=>hint,stop:(...args)=>calls.push(args),enqueue:fn=>jobs.push(fn)});
 schedule();const terminal=sessionEndInfo('insufficient_credits');calls.push([terminal.message,terminal.error]);current=false;jobs.shift()();assert.equal(calls.length,1);
 current=true;hint='Decart 额度或并发不足，请检查账户。';schedule();jobs.shift()();assert.equal(calls.at(-1)[0],hint);
 const length=calls.length;pending=true;schedule();jobs.shift()();assert.equal(calls.length,length);
 pending=false;schedule();current=false;jobs.shift()();assert.equal(calls.length,length);
});

import test from 'node:test';
import assert from 'node:assert/strict';
import {AutoRecordingGate} from '../src/auto-recording.js';
const video=()=>({readyState:2,videoWidth:1280,videoHeight:720});
const ready=()=>({enabled:true,connected:true,stalled:false,visible:true,supported:true,busy:false,videos:[video(),video()]});
test('automatic recording requires both decoded videos and an active visible AI session',()=>{
 const gate=new AutoRecordingGate();
 for(const change of [{enabled:false},{connected:false},{stalled:true},{visible:false},{supported:false},{busy:true},{videos:[]},{videos:[video(),{...video(),readyState:1}]},{videos:[{...video(),videoWidth:0},video()]}])assert.equal(gate.take({...ready(),...change}),false);
 assert.equal(gate.take(ready()),true);
});
test('automatic recording never restarts after stop, failure, background or reconnect in the same session',()=>{
 const gate=new AutoRecordingGate();assert.equal(gate.take(ready()),true);
 assert.equal(gate.take({...ready(),connected:false}),false);assert.equal(gate.take(ready()),false);
 gate.reset();assert.equal(gate.take(ready()),true);
});
test('manual recording or manual stop suppresses later automatic starts until the next try-on',()=>{
 const gate=new AutoRecordingGate();gate.suppress();assert.equal(gate.take(ready()),false);
 gate.reset();assert.equal(gate.take(ready()),true);
});

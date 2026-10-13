import {test} from 'node:test';
import assert from 'node:assert/strict';
import {ComparisonRecorder,recordingMime,recordingLayout,fitVideo,RECORDING_MAX_MS,RECORDING_MAX_BYTES} from '../src/comparison-recorder.js';

function fixture(){
 const context={fillRect(){},fillText(){},save(){},restore(){},translate(){},scale(){},drawImage(){}};
 const owned={stops:0,stop(){this.stops++;}},source={stops:0,stop(){this.stops++;}};
 const state={now:0,callback:null,captureCount:0,failStart:false,clips:[],errors:[]};
 const videos=[0,1].map(()=>({readyState:2,videoWidth:1280,videoHeight:720,srcObject:{getTracks:()=>[source]}}));
 class Recorder{
  static isTypeSupported(type){return type.startsWith('video/webm');}
  constructor(stream,options){this.state='inactive';this.mimeType=options.mimeType;state.native=this;}
  start(){if(state.failStart)throw Error('Encoder unavailable');this.state='recording';}
  stop(){this.state='inactive';queueMicrotask(()=>{this.ondataavailable?.({data:new Blob(['final'])});this.onstop?.();});}
 }
 const env={MediaRecorder:Recorder,HTMLCanvasElement:{prototype:{captureStream(){}}},Blob,performance:{now:()=>state.now},setInterval(fn){state.callback=fn;return 1;},clearInterval(){state.callback=null;},document:{createElement(){return {getContext:()=>context,captureStream(){state.captureCount++;return {getTracks:()=>[owned]};}};}}};
 const recorder=new ComparisonRecorder({getVideos:()=>videos,env,onClip:clip=>state.clips.push(clip),onError:error=>state.errors.push(error)});
 return {recorder,state,videos,owned,source};
}
test('recording chooses supported containers and keeps landscape/portrait content proportional',()=>{
 assert.equal(recordingMime(undefined),null);
 assert.equal(recordingMime(class{static isTypeSupported(type){return type==='video/mp4';}}),'video/mp4');
 assert.deepEqual(recordingLayout(1280,720),{width:1280,height:408,panelWidth:640,videoHeight:360,headerHeight:48});
 assert.equal(recordingLayout(720,1280).height,1008);
 const calls=[];fitVideo({save(){},restore(){},translate(){},scale(...a){calls.push(a);},drawImage(...a){calls.push(a.slice(1));}},{videoWidth:720,videoHeight:1280},640,48,640,960,true);
 assert.deepEqual(calls[0],[-1,1]);assert.equal(calls[1][2]/calls[1][3],720/1280);assert.equal(calls[1][3],960);
});
test('no recording starts before two decoded videos; final encoder chunk is retained and source tracks stay live',async()=>{
 const {recorder,state,videos,owned,source}=fixture();videos[1].readyState=0;
 assert.throws(()=>recorder.start(),/NO_FRAMES/);assert.equal(state.captureCount,0);videos[1].readyState=2;recorder.start();
 state.native.ondataavailable({data:new Blob(['first'])});state.now=2500;
 const finished=recorder.stop('session-ended');assert.equal(recorder.state,'stopping');assert.throws(()=>recorder.start(),/BUSY/);
 const clip=await finished;assert.equal(await clip.blob.text(),'firstfinal');assert.equal(clip.extension,'webm');assert.equal(clip.durationMs,2500);assert.equal(clip.reason,'session-ended');
 assert.equal(recorder.state,'idle');assert.equal(owned.stops,1);assert.equal(source.stops,0);assert.equal(state.clips.length,1);
});
test('encoder start failure releases capture tracks and permits retry',async()=>{
 const {recorder,state,owned}=fixture();state.failStart=true;assert.throws(()=>recorder.start(),/START_FAILED/);assert.equal(owned.stops,1);assert.equal(recorder.busy,false);
 state.failStart=false;recorder.start();await recorder.stop();assert.equal(state.clips.length,1);assert.equal(owned.stops,2);
});
test('time and memory limits finalize recording without stopping source tracks',async()=>{
 const f=fixture();f.recorder.start();f.state.now=RECORDING_MAX_MS;f.state.callback();const timed=await f.recorder.finished;
 assert.equal(timed.reason,'time-limit');assert.equal(f.source.stops,0);
 f.recorder.start();f.state.native.ondataavailable({data:{size:RECORDING_MAX_BYTES}});const sized=await f.recorder.finished;assert.equal(sized.reason,'size-limit');assert.equal(f.source.stops,0);
});
test('lost frames keep a downloadable partial clip; page disposal suppresses new downloads',async()=>{
 const f=fixture();f.recorder.start();f.videos[1].readyState=0;f.state.callback();assert.equal((await f.recorder.finished).reason,'interrupted');
 f.videos[1].readyState=2;f.recorder.start();f.recorder.dispose();assert.equal(await f.recorder.finished,null);assert.equal(f.state.clips.length,1);assert.equal(f.source.stops,0);
});
test('encoder failure exposes no successful clip and cleans its owned stream',async()=>{
 const f=fixture();f.recorder.start();f.state.native.onerror();assert.equal(await f.recorder.finished,null);assert.equal(f.state.clips.length,0);assert.deepEqual(f.state.errors,['RECORDING_FAILED']);assert.equal(f.source.stops,0);assert.equal(f.owned.stops,1);
});

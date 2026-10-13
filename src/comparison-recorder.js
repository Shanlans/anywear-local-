// Browser-only compositing. This module never sends media or touches source tracks.
export const RECORDING_MAX_MS=300000,RECORDING_MAX_BYTES=96*1024*1024;
export function recordingMime(Recorder){
 if(typeof Recorder!=='function'||typeof Recorder.isTypeSupported!=='function')return null;
 return ['video/mp4','video/webm;codecs=vp8','video/webm'].find(type=>Recorder.isTypeSupported(type))||null;
}
export function recordingLayout(width,height){
 if(!(width>0&&height>0))throw Error('RECORDING_NO_FRAMES');
 const videoHeight=Math.round(Math.max(360,Math.min(960,640*height/width))/2)*2;
 return {width:1280,height:videoHeight+48,panelWidth:640,videoHeight,headerHeight:48};
}
export function fitVideo(ctx,video,x,y,width,height,mirror){
 const scale=Math.min(width/video.videoWidth,height/video.videoHeight),w=video.videoWidth*scale,h=video.videoHeight*scale;
 ctx.save();ctx.translate(x+width/2,y+height/2);if(mirror)ctx.scale(-1,1);ctx.drawImage(video,-w/2,-h/2,w,h);ctx.restore();
}
const ready=video=>video?.readyState>=2&&video.videoWidth>0&&video.videoHeight>0;
export class ComparisonRecorder{
 constructor({getVideos,getMirror=()=>false,getLabels=()=>['Original','AI'],onChange=()=>{},onClip=()=>{},onError=()=>{},env=globalThis}){
  Object.assign(this,{getVideos,getMirror,getLabels,onChange,onClip,onError,env});this.state='idle';this.durationMs=0;this.bytes=0;this.disposed=false;
 }
 get supported(){return !!recordingMime(this.env.MediaRecorder)&&typeof this.env.HTMLCanvasElement?.prototype?.captureStream==='function';}
 get busy(){return this.state!=='idle';}
 emit(){this.onChange({state:this.state,durationMs:this.durationMs,bytes:this.bytes,reason:this.reason});}
 start(){
  if(this.disposed||this.busy)throw Error('RECORDING_BUSY');
  if(!this.supported)throw Error('RECORDING_UNSUPPORTED');
  const videos=this.getVideos();if(videos.length!==2||!videos.every(ready))throw Error('RECORDING_NO_FRAMES');
  this.layout=recordingLayout(videos[0].videoWidth,videos[0].videoHeight);this.canvas=this.env.document.createElement('canvas');Object.assign(this.canvas,{width:this.layout.width,height:this.layout.height});this.ctx=this.canvas.getContext('2d');
  this.chunks=[];this.bytes=0;this.durationMs=0;this.failed=false;this.reason='manual';this.startedAt=this.env.performance.now();
  try{
   this.draw(videos);this.capture=this.canvas.captureStream(20);
   this.recorder=new this.env.MediaRecorder(this.capture,{mimeType:recordingMime(this.env.MediaRecorder),videoBitsPerSecond:4000000});
   this.finished=new Promise(resolve=>{this.resolveFinish=resolve;});
   this.recorder.ondataavailable=event=>{if(event.data?.size){this.chunks.push(event.data);this.bytes+=event.data.size;if(this.bytes>=RECORDING_MAX_BYTES)this.stop('size-limit');}};
   this.recorder.onerror=()=>{this.failed=true;this.stop('error');};
   this.recorder.onstop=()=>this.finish();
   this.recorder.start(1000);this.state='recording';this.emit();
   this.timer=this.env.setInterval(()=>{try{
    this.durationMs=this.env.performance.now()-this.startedAt;
    if(this.durationMs>=RECORDING_MAX_MS){this.stop('time-limit');return;}
    const current=this.getVideos();if(current.length!==2||!current.every(ready)){this.stop('interrupted');return;}
    this.draw(current);this.emit();
   }catch{this.failed=true;this.stop('error');}},50);
  }catch{
   this.release();if(this.recorder){this.recorder.onstop=null;this.recorder.ondataavailable=null;this.recorder.onerror=null;if(this.recorder.state!=='inactive')try{this.recorder.stop();}catch{}}
   this.recorder=null;this.state='idle';this.chunks=[];this.resolveFinish?.(null);this.emit();throw Error('RECORDING_START_FAILED');
  }
 }
 draw(videos){
  const ctx=this.ctx,{width,height,panelWidth,videoHeight,headerHeight}=this.layout;
  ctx.fillStyle='#111811';ctx.fillRect(0,0,width,height);ctx.fillStyle='#f6f5f0';ctx.font='20px sans-serif';ctx.textBaseline='middle';
  const labels=this.getLabels();ctx.fillText(labels[0],20,24);ctx.fillText(labels[1],panelWidth+20,24);
  const seconds=Math.floor(this.durationMs/1000),time=String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0');ctx.fillText(time,width-80,24);
  videos.forEach((v,i)=>fitVideo(ctx,v,i*panelWidth,headerHeight,panelWidth,videoHeight,this.getMirror()));ctx.fillStyle='#64735a';ctx.fillRect(panelWidth-1,headerHeight,2,videoHeight);
 }
 stop(reason='manual'){
  if(this.state==='idle')return Promise.resolve(null);if(this.state==='stopping')return this.finished;
  this.reason=reason;this.durationMs=this.env.performance.now()-this.startedAt;this.state='stopping';this.env.clearInterval(this.timer);this.emit();
  try{if(this.recorder.state!=='inactive')this.recorder.stop();}catch{this.failed=true;this.finish();}
  return this.finished;
 }
 release(){this.env.clearInterval(this.timer);this.capture?.getTracks().forEach(track=>track.stop());this.capture=null;}
 finish(){
  if(!this.recorder)return;const recorder=this.recorder;this.recorder=null;this.release();this.durationMs=this.env.performance.now()-this.startedAt;
  const mimeType=recorder.mimeType||recordingMime(this.env.MediaRecorder);const blob=this.bytes&&!this.failed&&!this.disposed?new this.env.Blob(this.chunks,{type:mimeType}):null;
  this.chunks=[];this.state='idle';const resolveFinish=this.resolveFinish;this.resolveFinish=null;
  const clip=blob?{blob,mimeType,extension:mimeType.startsWith('video/mp4')?'mp4':'webm',durationMs:this.durationMs,reason:this.reason,width:this.layout.width,height:this.layout.height}:null;
  if(!this.disposed){if(clip)this.onClip(clip);else this.onError('RECORDING_FAILED');this.emit();}resolveFinish?.(clip);
 }
 dispose(){this.disposed=true;this.stop('pagehide');this.release();}
}

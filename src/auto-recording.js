// At most one automatic attempt per user-started try-on; no camera access here.
export class AutoRecordingGate {
 constructor(){this.reset();}
 reset(){this.consumed=false;}
 suppress(){this.consumed=true;}
 take({enabled,connected,stalled,visible,supported,busy,videos}){
  if(this.consumed||!enabled||!connected||stalled||!visible||!supported||busy)return false;
  if(videos.length!==2||!videos.every(v=>v?.readyState>=2&&v.videoWidth>0&&v.videoHeight>0))return false;
  this.consumed=true;return true;
 }
}

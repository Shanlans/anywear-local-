// A late connect must never resurrect a cancelled session or overlap a new dial.
export class SessionLane {
 constructor(){this.version=0;this.pending=false;this.connection=null;}
 begin(){if(this.pending||this.connection)throw Error('SESSION_BUSY');this.pending=true;return ++this.version;}
 current(run){return run===this.version;}
 resolve(run,connection){this.pending=false;if(!this.current(run)){connection.disconnect();return false;}this.connection=connection;return true;}
 reject(){this.pending=false;}
 cancel(){++this.version;this.connection?.disconnect();this.connection=null;}
}
export function stallAction(ageMs,visible){return !visible?'none':ageMs>=15000?'stop':ageMs>=5000?'warn':'none';}
export function inputSize(mode,w,h){if(mode==='portrait')return {width:720,height:1280};return w>=h?{width:1280,height:720}:{width:720,height:1280};}
export function drawRegion(mode,w,h,outW,outH){const ratio=outW/outH;if(mode==='portrait'){const sw=Math.min(w,h*ratio);return {sx:(w-sw)/2,sy:(h-sw/ratio)/2,sw,sh:sw/ratio,dx:0,dy:0,dw:outW,dh:outH};}const scale=Math.min(outW/w,outH/h);return {sx:0,sy:0,sw:w,sh:h,dx:(outW-w*scale)/2,dy:(outH-h*scale)/2,dw:w*scale,dh:h*scale};}

export const MAX_TRY_ON_SECONDS=30;
export function sessionLimit(value){
 const seconds=Number(value);
 return Number.isFinite(seconds)&&seconds>0?Math.max(10,Math.min(MAX_TRY_ON_SECONDS,Math.floor(seconds))):MAX_TRY_ON_SECONDS;
}
// One deadline covers dialing, streaming, edits and reconnects.
export class SessionDeadline {
 constructor({now=()=>performance.now(),schedule=(fn,ms)=>globalThis.setTimeout(fn,ms),cancel=id=>globalThis.clearTimeout(id)}={}){this.now=now;this.schedule=schedule;this.cancel=cancel;this.version=0;this.until=null;this.timers=[];}
 start({seconds,current,onWarn,onExpire}){
  this.clear();const version=this.version,limit=sessionLimit(seconds);this.until=this.now()+limit*1000;
  const valid=()=>version===this.version&&current();
  this.timers.push(this.schedule(()=>{if(valid())onWarn();},(limit-5)*1000));
  this.timers.push(this.schedule(()=>{if(valid()){this.clear();onExpire();}},limit*1000));
 }
 get remaining(){return this.until===null?null:Math.max(0,Math.ceil((this.until-this.now())/1000));}
 clear(){++this.version;for(const timer of this.timers)this.cancel(timer);this.timers=[];this.until=null;}
}

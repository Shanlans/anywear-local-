export const RATE=0.02;
export function secondsBetween(start,end){return Math.max(0,(end-start)/1000);}
export function estimateSession(session,now=Date.now()){
 const elapsed=secondsBetween(session.startedAt,session.endedAt??now);
 const observed=(session.observedMs||0)+(session.generatingAt!=null?Math.max(0,now-session.generatingAt):0);
 const reported=session.hasReported?session.reportedSeconds:null;
 const seconds=reported??observed/1000;
 const known=session.sawGeneration===true;
 return {elapsed,seconds,cost:known?seconds*(session.rate??RATE):null,basis:reported!=null?'reported':'observed'};
}
export function summarize(sessions){const known=sessions.map(s=>estimateSession(s,s.endedAt)).filter(s=>s.cost!=null);const total=known.reduce((n,s)=>n+s.cost,0);return {total,average:known.length?total/known.length:null,count:sessions.length,priced:known.length,unknown:sessions.length-known.length};}

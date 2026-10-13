import {errorReason} from './diagnostics.js';
const apiHints={
  credit:'Decart 额度或并发不足，请检查账户。',
  auth:'Decart 身份验证失败，请检查密钥和权限。',
  origin:'Decart 拒绝当前网页来源，请检查令牌来源配置。',
  model:'当前试衣模型不可用，请检查模型配置与权限。'
};
export function apiFailureHint(error){return apiHints[errorReason(error)]||null;}
export function sessionEndInfo(reason,precedingHint=null){
 // SDK's policy_violation is a generic WebSocket 1008 close, not proof of
 // content moderation. Keep a preceding known API error; never echo raw text.
 if(reason==='policy_violation'){
  const preceding=Object.entries(apiHints).find(([,message])=>message===precedingHint);
  return {message:preceding?.[1]||'Decart 按服务端规则结束连接，具体原因未提供。请检查账户或联系平台支持。',error:true,code:'SESSION_END_POLICY_GENERIC',reason:preceding?.[0]||'unknown'};
 }
 const known={
  insufficient_credits:{message:'Decart 返回额度不足，已结束会话；请在平台检查额度后再开始。',error:true,code:'SESSION_END_INSUFFICIENT_CREDITS',reason:'credit'},
  session_limit:{message:'Decart 返回并发会话上限，已结束；请先结束其他试衣会话后再开始。',error:true,code:'SESSION_END_CONCURRENCY_LIMIT',reason:'credit'},
  moderation_violation:{message:'Decart 返回明确的内容审核终止，请检查参考图、提示词与平台使用规则。',error:true,code:'SESSION_END_MODERATION',reason:'unknown'}
 };
 return Object.hasOwn(known,reason)?known[reason]:{message:'Decart 已结束会话，可以重新预览。',error:false,code:'SESSION_END_UNKNOWN',reason:'unknown'};
}
// SDK 0.2.7 emits disconnected immediately before sessionEnded. Let that
// authoritative terminal reason finish cleanup first; never stop a newer run.
export function scheduleDisconnected({current,pending,message,stop,enqueue=queueMicrotask}){
 enqueue(()=>{if(current()&&!pending())stop(message()||'连接已断开，请重新预览和开始。',true);});
}

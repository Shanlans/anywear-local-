import {errorReason} from './diagnostics.js';
export function apiFailureHint(error){
 return {
  credit:'Decart 额度或并发不足，请检查账户。',
  auth:'Decart 身份验证失败，请检查密钥和权限。',
  origin:'Decart 拒绝当前网页来源，请检查令牌来源配置。',
  model:'当前试衣模型不可用，请检查模型配置与权限。'
 }[errorReason(error)]||null;
}
export function sessionEndInfo(reason){
 const known={
  insufficient_credits:{message:'Decart 返回额度不足，已结束会话；请在平台检查额度后再开始。',error:true,code:'SESSION_END_INSUFFICIENT_CREDITS',reason:'credit'},
  session_limit:{message:'Decart 返回并发会话上限，已结束；请先结束其他试衣会话后再开始。',error:true,code:'SESSION_END_CONCURRENCY_LIMIT',reason:'credit'},
  moderation_violation:{message:'Decart 因内容策略结束会话，请更换参考图或提示词后重试。',error:true,code:'SESSION_END_POLICY',reason:'unknown'},
  policy_violation:{message:'Decart 因内容策略结束会话，请更换参考图或提示词后重试。',error:true,code:'SESSION_END_POLICY',reason:'unknown'}
 };
 return Object.hasOwn(known,reason)?known[reason]:{message:'Decart 已结束会话，可以重新预览。',error:false,code:'SESSION_END_UNKNOWN',reason:'unknown'};
}
// SDK 0.2.7 emits disconnected immediately before sessionEnded. Let that
// authoritative terminal reason finish cleanup first; never stop a newer run.
export function scheduleDisconnected({current,pending,message,stop,enqueue=queueMicrotask}){
 enqueue(()=>{if(current()&&!pending())stop(message()||'连接已断开，请重新预览和开始。',true);});
}

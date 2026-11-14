/** No network here: only the explicitly approved Python host performs egress. */
import {createAssistantMessageEventStream} from '@earendil-works/pi-ai';
const bindings=new WeakMap();
export const isRemoteAdapter=(stream,host,model)=>{const b=bindings.get(stream);return !!b && (host===undefined || (b.host===host&&b.modelId===model?.id));};
export function createDeepSeekStream(host,modelId){
 if(!host||typeof host.call!=='function'||!['deepseek-v4-pro','deepseek-flash'].includes(modelId))throw new Error('MCIS_REMOTE_CONFIG');
 const stream=async(model,_context,options)=>{
  const out=createAssistantMessageEventStream();
  const base={role:'assistant',api:model.api,provider:'deepseek',model:modelId,timestamp:Date.now(),usage:{input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}}};
  try{
   if(options?.signal?.aborted)throw new Error();
   const r=await host.call({op:'model_request'});
   if(options?.signal?.aborted||!r||r.error||r.ok===false||r.configuredModel!==modelId||!['stop','tool_calls'].includes(r.finish_reason))throw new Error();
   const msg=r.message;if(!msg||msg.role!=='assistant')throw new Error();
   const content=[];
   if(msg.content!==null&&msg.content!==undefined){if(typeof msg.content!=='string')throw new Error();if(msg.content)content.push({type:'text',text:msg.content});}
   const calls=msg.tool_calls||[];if(!Array.isArray(calls)||calls.length>8)throw new Error();
   for(const call of calls){if(call.type!=='function'||typeof call.id!=='string'||typeof call.function?.name!=='string'||typeof call.function.arguments!=='string')throw new Error();content.push({type:'toolCall',id:call.id,name:call.function.name,arguments:JSON.parse(call.function.arguments)});}
   if((r.finish_reason==='tool_calls')!==Boolean(calls.length))throw new Error();
   const message={...base,content,stopReason:calls.length?'toolUse':'stop'};
   out.push({type:'start',partial:message});out.push({type:'done',reason:message.stopReason,message});
  }catch{out.push({type:'error',reason:'error',error:{...base,content:[],stopReason:'error',errorMessage:'MCIS remote host stopped'}});}
  return out;
 };
 bindings.set(stream,{host,modelId});return stream;
}

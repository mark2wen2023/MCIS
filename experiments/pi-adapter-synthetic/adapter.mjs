// Isolated proof of concept. No real model or production data connector.
import {Agent} from '@earendil-works/pi-agent-core';

const schema = properties => ({type:'object',properties,required:Object.keys(properties),additionalProperties:false});
const s = {type:'string',minLength:1,maxLength:200};
const model={id:'scripted-not-llm',api:'openai-completions',provider:'offline',contextWindow:10000,maxTokens:256};

// All parameters and authorization are supplied by trusted application code, never the model.
// scope contains a single frozen synthetic case. Identity and synthetic flag are NOT security controls.
export function createAdapter({scope, streamFn, maxCalls=8, onEvent=()=>{}}) {
  if (!scope || scope.synthetic !== true || typeof scope.caseId !== 'string' || !scope.caseId || !Array.isArray(scope.sources) || typeof streamFn !== 'function' || !Number.isSafeInteger(maxCalls) || maxCalls<1 || maxCalls>100) throw Error('invalid configuration');
  const snapshot=structuredClone(scope); const delivered=new Set(), candidates=[], events=[];
  let calls=0, modelCalls=0, stopped=false, active=false, used=false, terminal='completed';
  const emit=(type, extra={})=>{const e={type,...extra};events.push(e);try {onEvent({...e});} catch {} }; // metadata only
  const check=(a)=>{if(stopped) throw Error('cancelled'); if(a.caseId!==snapshot.caseId) throw Error('case denied');};
  const tool=(name,properties,fn)=>({name,label:name,description:`Synthetic-only ${name}`,parameters:schema(properties),execute:async(_id,a,signal)=>{check(a);if(signal?.aborted) throw Error('cancelled');return {content:[{type:'text',text:JSON.stringify(await fn(a,signal))}],details:{}};}});
  const tools=[
    tool('read_report',{caseId:s,sourceId:s}, async a=>read(a,'report')),
    tool('read_evidence',{caseId:s,sourceId:s}, async a=>read(a,'evidence')),
    tool('submit_candidate',{caseId:s,text:{type:'string',minLength:1,maxLength:4000},sourceId:s,version:s}, async a=>{
      if(!delivered.has(JSON.stringify([a.sourceId,a.version]))) throw Error('source version not delivered');
      const candidate={caseId:snapshot.caseId,text:a.text,sourceId:a.sourceId,version:a.version,status:'candidate_requires_human_review'}; candidates.push(candidate);return candidate;
    })
  ];
  function read(a,kind){const source=snapshot.sources.find(x=>x.kind===kind && x.id===a.sourceId);if(!source || typeof source.version!=='string' || !source.version || typeof source.text!=='string') throw Error('source denied');delivered.add(JSON.stringify([source.id,source.version]));return {id:source.id,version:source.version,text:source.text};}
  const agent=new Agent({initialState:{model,tools},streamFn:async (...args)=>{
    if(++modelCalls>maxCalls+1){stopped=true;terminal='budget_exhausted';emit('model_budget_exhausted');throw Error('model-call budget exhausted');}
    const source=await streamFn(...args); let final;
    return { [Symbol.asyncIterator]:()=>source[Symbol.asyncIterator](), result:async()=>{
      if(!final) final=Promise.resolve(source.result()).then(message=>{
        if(message.content.filter(part=>part.type==='toolCall').length>maxCalls){
          stopped=true;terminal='budget_exhausted';emit('batch_budget_exhausted');
          return {...message,content:[],stopReason:'error',errorMessage:'tool-call batch budget exhausted'};
        }
        return message;
      });
      return final;
    }};
  },beforeToolCall:({toolCall,args})=>{
    if(stopped) return {block:true,reason:'cancelled',terminate:true};
    if(++calls>maxCalls){stopped=true;terminal='budget_exhausted';emit('budget_exhausted');return {block:true,reason:'tool-call budget exhausted',terminate:true};}
    emit('tool_attempt',{name:toolCall.name,call:calls});
    if(args.caseId!==snapshot.caseId){emit('case_denied');return {block:true,reason:'case denied',terminate:true};}
  }});
  agent.subscribe(e=>{if(e.type==='tool_execution_end') emit('tool_end',{name:tools.some(t=>t.name===e.toolName)?e.toolName:'unknown',isError:!!e.isError});});
  return {
    async run(prompt){if(active || stopped || used) throw Error('adapter unavailable'); used=true;active=true;emit('run_started');try{await agent.prompt(prompt);if(terminal==='completed' && agent.state.messages.some(m=>m.role==='assistant' && m.errorMessage)) terminal='provider_error';emit('run_ended',{status:terminal});}finally{active=false;}return {status:terminal,candidates:structuredClone(candidates),events:structuredClone(events),messages:structuredClone(agent.state.messages)};},
    cancel(){stopped=true;terminal='cancelled';emit('cancelled');agent.abort();},
  };
}

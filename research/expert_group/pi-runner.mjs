// No credentials or network transport: every model/tool operation is authorized by Python.
import readline from 'node:readline';
import { Agent } from '@earendil-works/pi-agent-core';
import { createAssistantMessageEventStream } from '@earendil-works/pi-ai';
const lines = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
const iterator = lines[Symbol.asyncIterator]();
async function read() {
  const item = await iterator.next();
  if (item.done || item.value.length > 262144) throw new Error('host_protocol');
  return JSON.parse(item.value);
}
async function rpc(value) {
  process.stdout.write(JSON.stringify(value) + '\n');
  return read();
}
try {
  const config = await read();
  const model = {id: config.model, api:'openai-completions', provider:'deepseek',baseUrl:'https://api.deepseek.com',reasoning:false,input:['text'],cost:{input:0,output:0,cacheRead:0,cacheWrite:0},contextWindow:8192,maxTokens:2400};
  const tools = config.tools.map(({function: fn}) => ({name:fn.name,label:fn.name,description:fn.description,parameters:fn.parameters,
    execute:async (id,args) => {
      const response = await rpc({op:'tool',id,name:fn.name,args});
      return {content:[{type:'text',text:JSON.stringify(response.result)}],details:{}};
    }}));
  const agent = new Agent({initialState:{systemPrompt:config.systemPrompt,model,tools},toolExecution:'sequential',identity:{attribution:null},
    streamFn:async () => {
      const stream = createAssistantMessageEventStream();
      void (async()=>{
        try {
          const {message} = await rpc({op:'model'});
          const content=[];
          if (message.content) content.push({type:'text',text:message.content});
          for (const call of message.tool_calls ?? []) content.push({type:'toolCall',id:call.id,name:call.function.name,arguments:JSON.parse(call.function.arguments)});
          const out={role:'assistant',content,api:model.api,provider:model.provider,model:model.id,usage:{input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}},stopReason:message.tool_calls?.length?'toolUse':'stop',timestamp:Date.now()};
          stream.push({type:'start',partial:out});
          stream.push({type:'done',reason:out.stopReason,message:out});
          stream.end();
        } catch {
          stream.push({type:'error',reason:'error',error:{role:'assistant',content:[],api:model.api,provider:model.provider,model:model.id,stopReason:'error',errorMessage:'host_protocol',timestamp:Date.now(),usage:{input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0,cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0}}}});
          stream.end();
        }
      })();
      return stream;
    }});
  await agent.prompt('Review every item in the fixed public packet. Call read_packet first.');
  const last = agent.state.messages.at(-1);
  if (last?.role !== 'assistant' || last.stopReason !== 'stop') throw new Error('incomplete');
  const text = last.content.filter(x=>x.type==='text').map(x=>x.text).join('');
  process.stdout.write(JSON.stringify({op:'done',text})+'\n');
  lines.close();
} catch {
  lines.close();
  process.exitCode=4;
}

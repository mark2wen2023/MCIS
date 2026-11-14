/** Explicit test-only public-report UI acceptance. No credentials or case data in logs. */
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {tmpdir} from 'node:os';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {join,resolve} from 'node:path';
import {createExtractionWorkingPort} from '../src/extractionWorking/hostPort';
import {createWorkingArchivePort} from '../src/workingArchive/hostPort';
const say=(value:unknown)=>process.stdout.write(JSON.stringify(value)+'\n');
const check=(condition:unknown)=>{if(!condition)throw new Error('MCIS_PROBE_FAILED')};
const canonical=(v:any):string=>Array.isArray(v)?'['+v.map(canonical).join(',')+']':v&&typeof v==='object'?'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}':JSON.stringify(v);
// Third-party/UI diagnostics must not echo source, model text, credentials or assertion diffs.
console.error=()=>{};console.warn=()=>{};console.log=()=>{};
async function main(){
 const args=process.argv.slice(2);check(args.length===1&&['--fixture','--approved-public-ui'].includes(args[0]));const fixture=args[0]==='--fixture';
 const runtime=process.env.MCIS_PI_RUNTIME||fileURLToPath(new URL('../../tools/pi-transcript/',import.meta.url));
 const {createRunReceipt}=await import(pathToFileURL(join(runtime,'run-receipt.mjs')).href);
 const {runTranscript}=await import(pathToFileURL(join(runtime,'runner.mjs')).href);
 const {createDeepSeekStream}=await import(pathToFileURL(join(runtime,'deepseek-adapter.mjs')).href);
 const receipt=createRunReceipt(tmpdir());say({status:'receipt_created',runId:receipt.id,mockInference:fixture});
 let child:any=null,lines:any=null,window:any=null,root:any=null,secret:string|null=null,closed=false,cleaned=false,models=0,tools=0,proposals=0,citations=0,watchdog:any;
 let pending:any=null;const queue:any[]=[];let childFailure=false;
 try{
  if(!fixture){
   const input=createInterface({input:process.stdin});
   try{secret=await new Promise<string>((ok,fail)=>{const timer=setTimeout(()=>fail(new Error('MCIS_PROBE_FAILED')),30000);input.once('line',line=>{clearTimeout(timer);try{const v=JSON.parse(line);check(v&&typeof v==='object'&&!Array.isArray(v)&&Object.keys(v).length===1&&typeof v.apiKey==='string'&&v.apiKey.length>0&&v.apiKey.length<=200);ok(v.apiKey)}catch{fail(new Error('MCIS_PROBE_FAILED'))}});input.once('close',()=>{clearTimeout(timer);fail(new Error('MCIS_PROBE_FAILED'))})})}
   finally{input.close();process.stdin.pause()}
  }
  const python=process.env.MCIS_HOST_PYTHON,service=process.env.MCIS_HOST_SERVICE;check(python&&service);
  const env:Record<string,string>={PATH:process.env.PATH||'',LANG:'C.UTF-8',PYTHONPATH:resolve(service!)};
  for(const k of ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','http_proxy','https_proxy','all_proxy','no_proxy','SSL_CERT_FILE','SSL_CERT_DIR'])if(process.env[k])env[k]=process.env[k]!;
  child=spawn(python!,[join(runtime,'public-ui-host.py'),fixture?'--fixture':'--approved-public-ui'],{env,stdio:['pipe','pipe','pipe']});
  child.stderr.resume();let bytes=0;
  const fail=()=>{childFailure=true;pending?.fail(new Error('MCIS_PROBE_FAILED'));pending=null};
  child.on('error',fail);child.on('close',fail);child.stdin.on('error',fail);
  child.stdout.on('data',(chunk:Buffer)=>{bytes+=chunk.length;if(bytes>32*1024*1024){fail();child.kill()}});
  lines=createInterface({input:child.stdout});
  lines.on('line',(line:string)=>{try{check(Buffer.byteLength(line)<=12*1024*1024);const value=JSON.parse(line);if(pending){const p=pending;pending=null;p.ok(value)}else{check(queue.length<4);queue.push(value)}}catch{fail();child.kill()}});
  const next=()=>queue.length?Promise.resolve(queue.shift()):childFailure?Promise.reject(new Error('MCIS_PROBE_FAILED')):new Promise<any>((ok,failRead)=>{check(!pending);const timer=setTimeout(()=>{pending=null;failRead(new Error('MCIS_PROBE_FAILED'))},125000);pending={ok:(v:any)=>{clearTimeout(timer);ok(v)},fail:(e:any)=>{clearTimeout(timer);failRead(e)}};});
  let sending=false;
  const exchange=async(value:any)=>{check(!sending&&!childFailure);sending=true;try{const encoded=JSON.stringify(value)+'\n';check(Buffer.byteLength(encoded)<=12*1024*1024);child.stdin.write(encoded);return await next()}finally{sending=false}};
  watchdog=setTimeout(()=>{fail();child.kill()},240000);
  if(!fixture){child.stdin.write(JSON.stringify({apiKey:secret})+'\n');secret=null}
  const ready=await next();check(ready.ready===true&&ready.fixture===fixture&&ready.mode===(fixture?'fixture':'remote-deepseek')&&ready.transportMocked===fixture&&ready.inferencePerformed===false&&ready.configuredModel==='deepseek-v4-pro'&&ready.completionMode==='validated-reference'&&ready.excerptSha256==='c158ad790b5605dc4eea9303f9dc3748bb9f5ce07b969fd10f30cee9d6c45748'&&ready.source==='https://www.sh.msa.gov.cn/sgdc/104170.jhtml'&&ready.inputMeaning==='public-report-excerpt-not-witness-interview');
  receipt.append('host_ready');
  const host={call:async(command:any)=>{
   if(command.op==='model_request'){models++;receipt.append('model_request_started',{models,tools})}
   if(command.op==='tool')tools++;
   const result=await exchange(command);
   if(command.op==='model_request')receipt.append('model_request_returned',{models,tools});
   if(command.op==='tool')receipt.append('tool_returned',{models,tools});
   check(result.ok!==false);return result;
  }};
  const model={id:'deepseek-v4-pro',api:'openai-completions',provider:'deepseek',baseUrl:'https://api.deepseek.com',reasoning:false,input:['text'],cost:{input:0,output:0,cacheRead:0,cacheWrite:0},contextWindow:8192,maxTokens:4096};
  const result=await runTranscript({host,model,stream:createDeepSeekStream(host,model.id),mode:'remote-deepseek',finalMode:'validated-reference'});
  const accepted=result.result,working=accepted.workingReady;proposals=accepted.proposals.length;citations=accepted.citations.length;
  check(accepted.status==='PendingReview'&&accepted.saved===false&&accepted.factVerified===false&&accepted.completionMode==='validated-reference'&&accepted.providerMode==='remote-deepseek'&&result.realPi===true&&result.realModel===true&&proposals>=1&&proposals<=20&&citations===proposals);
  check(working&&working.saved===true&&working.factActivated===false&&working.reviewOrigin==='scripted_test'&&working.proposals===proposals&&working.citations===citations&&typeof working.proposalId==='string');
  const quoteSnapshot=accepted.proposals.map((p:any)=>p.quote);check(quoteSnapshot.every((q:any)=>typeof q==='string'));
  receipt.append('model_result_verified',{models,tools,proposals,citations});
  // Model/disclosure objects stay outside the rendered component tree.
  const {Window}=await import(process.env.MCIS_HAPPY_DOM_PATH||'happy-dom');window=new Window({url:'http://localhost'});
  for(const k of ['window','document','navigator','HTMLElement','HTMLTextAreaElement','Event','MouseEvent'])Object.defineProperty(globalThis,k,{value:window[k]??window,writable:true,configurable:true});(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true;
  const React=require('react'),{act}=React,{createRoot}=require('react-dom/client');
  const {ExtractionWorking}=require('../src/extractionWorking/ExtractionWorking');const {WorkingArchive}=require('../src/workingArchive/WorkingArchive');
  const container=document.createElement('div');document.body.append(container);root=createRoot(container);
  const pause=()=>new Promise(ok=>setTimeout(ok,20));
  const waitFor=async(f:()=>boolean)=>{const deadline=Date.now()+20000;while(!f()&&Date.now()<deadline){await act(async()=>{await pause()})}check(f())};
  const click=async(label:string)=>{await act(async()=>{const button=[...container.querySelectorAll('button')].find(b=>b.textContent===label);check(button&&!button.disabled);button!.click();await pause()})};
  const render=async(element:any)=>act(async()=>root.render(element));
  let reviewResponse:any=null,archiveResponse:any=null;
  const reviewPort=createExtractionWorkingPort(ready.reviewScope,async(request:any)=>{const r=await exchange({channel:'review',request});reviewResponse=r;return r},'remote-deepseek');
  const archivePort=createWorkingArchivePort(ready.archiveScope,async(request:any)=>{const r=await exchange({channel:'archive',request});archiveResponse=r;return r});
  await render(<ExtractionWorking port={reviewPort}/>);await click('刷新工作提案目录');await waitFor(()=>!!container.querySelector('button[aria-label^="打开 "]'));await click('打开工作提案');await waitFor(()=>container.querySelectorAll('article').length===proposals);
  check(JSON.stringify([...container.querySelectorAll('blockquote')].map(e=>e.textContent))===JSON.stringify(quoteSnapshot));check(reviewResponse.body.proposalId===working.proposalId&&reviewResponse.body.revision===0);
  await act(async()=>{[...container.querySelectorAll('textarea')].forEach(t=>{t.value='自动化验收脚本：待调查员核实，非真人审核或事实确认。';t.dispatchEvent(new window.Event('input',{bubbles:true}))})});
  await click('追加工作复核，不覆盖历史');await waitFor(()=>container.textContent?.includes('工作复核日志已保存')===true);
  check(reviewResponse.body.revision===1&&reviewResponse.body.factActivated===false&&reviewResponse.body.reviews[0].reviewOrigin==='scripted_test'&&reviewResponse.body.reviews[0].decisions.length===proposals&&reviewResponse.body.reviews[0].decisions.every((d:any)=>d.decision==='needs_verification'));
  await render(<ExtractionWorking/>);await render(<ExtractionWorking port={reviewPort}/>);await click('刷新工作提案目录');await waitFor(()=>!!container.querySelector('button[aria-label^="打开 "]'));await click('打开工作提案');await waitFor(()=>container.querySelectorAll('article').length===proposals);
  check(JSON.stringify([...container.querySelectorAll('blockquote')].map(e=>e.textContent))===JSON.stringify(quoteSnapshot));check(container.textContent?.includes('自动化验收脚本，非真人审核'));check(reviewResponse.body.revision===1);
  receipt.append('ui_review_verified',{models,tools,proposals,citations});
  let downloaded:Uint8Array|undefined;
  await render(<WorkingArchive port={archivePort} onDownload={(b:Uint8Array)=>{downloaded=b.slice()}}/>);await click('导出补充包');await waitFor(()=>container.textContent?.includes('下载本地JSON补充包')===true);await click('下载本地JSON补充包');await waitFor(()=>!!downloaded);
  const payload=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(downloaded)).payload;check(payload.format==='extraction-working-supplement-v2'&&payload.authority==='historical-untrusted-no-activation'&&payload.proposals.length===1);
  const exported=payload.proposals[0];check(exported.result.providerMode==='remote-deepseek'&&canonical(exported.result.proposals)===canonical(accepted.proposals)&&canonical(exported.result.citations)===canonical(accepted.citations)&&exported.reviews[0].reviewOrigin==='scripted_test');
  const file=new window.File([downloaded!],'public-working-history.json',{type:'application/json'});const input=container.querySelector('input')!;Object.defineProperty(input,'files',{value:[file],configurable:true});await act(async()=>{input.dispatchEvent(new window.Event('change',{bubbles:true}));await pause()});await waitFor(()=>container.textContent?.includes('尚未导入')===true);
  await click('导入为未认证历史');await waitFor(()=>container.textContent?.includes('历史补充包已保存')===true);check(archiveResponse.body.activated===false&&archiveResponse.body.status==='imported_untrusted_history');
  await click('刷新历史目录');await waitFor(()=>container.textContent?.includes('打开历史补充包')===true);await click('打开历史补充包');await waitFor(()=>container.querySelectorAll('blockquote').length===proposals);
  check(archiveResponse.body.activated===false&&archiveResponse.body.historicalClaimsVerified===false&&archiveResponse.body.payload.proposals[0].result.providerMode==='remote-deepseek'&&canonical(archiveResponse.body.payload.proposals[0].result.proposals)===canonical(accepted.proposals)&&canonical(archiveResponse.body.payload.proposals[0].result.citations)===canonical(accepted.citations));check(JSON.stringify([...container.querySelectorAll('blockquote')].map(e=>e.textContent))===JSON.stringify(quoteSnapshot));check(container.textContent?.includes('脚本测试意见，非真人审核'));check(window.localStorage.length===0&&window.sessionStorage.length===0);
  receipt.append('archive_roundtrip_verified',{models,tools,proposals,citations});
  await act(async()=>root.unmount());root=null;await window.happyDOM.abort();window.close();window=null;downloaded=undefined;
  const cleanup=await exchange({channel:'close'});check(cleanup.closed===true&&cleanup.cleanupConfirmed===true&&cleanup.temporaryStorageRemoved===true);cleaned=true;receipt.append('cleanup_verified',{models,tools,proposals,citations});
  child.stdin.end();
  await new Promise<void>((ok,fail)=>{if(child.exitCode!==null){child.exitCode===0?ok():fail(new Error('MCIS_PROBE_FAILED'));return}const timer=setTimeout(()=>fail(new Error('MCIS_PROBE_FAILED')),3000);child.once('close',(code:number|null)=>{clearTimeout(timer);code===0?ok():fail(new Error('MCIS_PROBE_FAILED'))})});
  receipt.append('accepted_pending_review',{models,tools,proposals,citations});closed=true;
  say({status:'accepted_pending_review',runId:receipt.id,mockInference:fixture,transportMocked:fixture,realModel:!fixture,realPi:true,providerRequests:fixture?0:models,modelRounds:models,tools,proposals,citations,uiReviewVerified:true,archiveV2Verified:true,reviewActor:'scripted_test_not_human',factActivated:false,cleanupConfirmed:true,processExitVerified:true,browserEngine:false,source:'https://www.sh.msa.gov.cn/sgdc/104170.jhtml',excerptSha256:'c158ad790b5605dc4eea9303f9dc3748bb9f5ce07b969fd10f30cee9d6c45748'});
 }catch{
  try{receipt.append('not_accepted',{models:Math.min(models,4),tools:Math.min(tools,8)},'MCIS_PROBE_FAILED')}catch{}
  say({status:'not_accepted',runId:receipt.id,mockInference:fixture,providerRequestAttempts:fixture?0:models,modelRounds:models,tools,cleanupConfirmed:cleaned,outcomeMayBeUnknown:!cleaned,errorCode:'MCIS_PROBE_FAILED'});process.exitCode=1;
 }finally{
  secret=null;clearTimeout(watchdog);receipt.close();if(root)try{root.unmount()}catch{};if(window)try{await window.happyDOM.abort();window.close()}catch{};
  pending?.fail(new Error('MCIS_PROBE_FAILED'));pending=null;lines?.close();if(child){child.stdin.end();if(!closed)child.kill();else if(child.exitCode===null){await new Promise<void>(done=>{const timer=setTimeout(()=>{child.kill();done()},2000);child.once('close',()=>{clearTimeout(timer);done()})})}}
 }
}
main().catch(()=>{say({status:'not_accepted',errorCode:'MCIS_PROBE_FAILED'});process.exitCode=1});

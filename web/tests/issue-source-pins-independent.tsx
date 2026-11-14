import assert from 'node:assert/strict';
const {Window}=await import(process.env.MCIS_HAPPY_DOM_PATH||'happy-dom');
const window=new Window({url:'http://localhost'});
for(const key of ['window','document','navigator','HTMLElement','HTMLTextAreaElement','Event','MouseEvent'])Object.defineProperty(globalThis,key,{value:(window as any)[key]??window,writable:true,configurable:true});
(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true;
const React=require('react');const {act}=React;const {createRoot}=require('react-dom/client');
const {IssueWorkspace}=require('../src/issueWorkspace/IssueWorkspace');
const {createRehearsalPort,parse}=require('../src/issueWorkspace/model');
const host=document.createElement('div');document.body.append(host);const root=createRoot(host);
async function render(props:any){await act(async()=>root.render(<IssueWorkspace {...props}/>))}
async function note(text:string){await act(async()=>{const el=host.querySelector('textarea')!;Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value')!.set!.call(el,text);el.dispatchEvent(new window.Event('input',{bubbles:true}));})}
async function kind(value:string){await act(async()=>{const el=host.querySelector('select')!;el.value=value;el.dispatchEvent(new window.Event('change',{bubbles:true}));})}
async function click(text:string){await act(async()=>{const el=[...host.querySelectorAll('button')].find(x=>x.textContent===text)!;el.dispatchEvent(new window.MouseEvent('click',{bubbles:true}));})}
const submit='追加记录，不覆盖历史';
const {SourceSelectionChanged,parseSources}=require('../src/issueWorkspace/model');const {createIssueHostPort}=require('../src/issueWorkspace/hostPort');
let checks=0;const check=(x:any,m:string)=>{assert(x,m);checks++};
const scope={profile:'mcis-issue-host-trial-v1',contextId:'00000000-0000-0000-0000-000000000100',caseId:'CASE-ISSUE-FICTIONAL',productionLogin:false};
const item={evidenceId:'EV-001',sourceIncarnation:'00000000-0000-0000-0000-000000000101',sourceSha256:'a'.repeat(64),mediaKind:'csv',byteLength:12,registeredUtc:'2026-11-14T00:00:00Z'};
const body={profile:'trial-issue-sources-v1',caseId:scope.caseId,scope:'current-local-supported-candidates-only',items:[item]};
const cmd={caseId:scope.caseId,issueId:'00000000-0000-0000-0000-000000000102',operationId:'00000000-0000-0000-0000-000000000103',expectedRevision:0,entry:{kind:'judgment',note:'draft',sourceIds:['EV-001'],againstJudgment:null,outcome:null},sourcePins:[{evidenceId:item.evidenceId,sourceIncarnation:item.sourceIncarnation,sourceSha256:item.sourceSha256}]};
const conflict=(m:any)=>({...scope,requestId:m.requestId,ok:false,code:'ISSUE_SOURCE_SELECTION_CHANGED',status:409});
for(const edit of [(c:any)=>delete c.sourcePins,(c:any)=>c.sourcePins[0].sourceIncarnation='wrong',(c:any)=>c.sourcePins[0].sourceSha256='wrong',(c:any)=>c.sourcePins[0].evidenceId='OTHER',(c:any)=>c.sourcePins.push(c.sourcePins[0]),(c:any)=>c.sourcePins[0].token='SECRET']){let sent=false;const c=structuredClone(cmd);edit(c);const p=createIssueHostPort(scope,async()=>{sent=true});await assert.rejects(p.save(c));check(!sent,'malformed pins not sent')}
await assert.rejects(createIssueHostPort(scope,async()=>{throw new SourceSelectionChanged()}).save(cmd),(e:any)=>!(e instanceof SourceSelectionChanged));checks++;
for(const edit of [(r:any)=>r.requestId='wrong',(r:any)=>r.contextId='wrong',(r:any)=>r.caseId='OTHER',(r:any)=>r.status=403,(r:any)=>r.productionLogin=true]){await assert.rejects(createIssueHostPort(scope,async(m:any)=>{const r=conflict(m);edit(r);return r}).save(cmd),(e:any)=>!(e instanceof SourceSelectionChanged));checks++}
await assert.rejects(createIssueHostPort(scope,async(m:any)=>conflict(m)).save(cmd),(e:any)=>e instanceof SourceSelectionChanged);checks++;
for(const inc of [undefined,'-'.repeat(36),7]){const b=structuredClone(body);b.items[0].sourceIncarnation=inc as any;assert.throws(()=>parseSources(b,scope.caseId));checks++}
const port=createIssueHostPort(scope,async(m:any)=>m.action==='sources'?{...scope,requestId:m.requestId,ok:true,body}:conflict(m));
await render({port,contextKey:scope.contextId});await click('读取当前来源');await act(async()=>host.querySelector('input')!.dispatchEvent(new window.MouseEvent('click',{bubbles:true})));await note('retain this draft');await click(submit);check((host.querySelector('textarea') as HTMLTextAreaElement).value==='retain this draft','conflict retains note');check(!host.querySelector('textarea')!.disabled,'first conflict allows reselect');check(host.querySelectorAll('input').length===0,'conflict clears sources');check(!host.textContent!.includes('按原操作重试'),'first explicit conflict clears pending');
const mem=createRehearsalPort();let first=true;const seen:any[]=[];const unknown={sources:async()=>body,read:mem.read,save:async(c:any)=>{seen.push(structuredClone(c));const r=await mem.save(c);if(first){first=false;throw Error('lost')}return r}};
await render({port:unknown,contextKey:'unknown'});await click('读取当前来源');await act(async()=>host.querySelector('input')!.dispatchEvent(new window.MouseEvent('click',{bubbles:true})));await note('frozen pins');await click(submit);await click('按原操作重试');assert.deepEqual(seen[0],seen[1]);checks++;assert.deepEqual(seen[0].sourcePins,cmd.sourcePins);checks++;
await act(async()=>root.unmount());await window.happyDOM.abort();window.close();console.log(checks+' independent source pin checks passed');process.exit(0);

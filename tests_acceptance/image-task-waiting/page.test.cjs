// Actual page query callback, in-memory Promise seam; no network/application/media.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/image_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 const requests=[];let fetches=0;
 class Element{constructor(){this.value='';this.textContent='';this.events={}}addEventListener(n,f){(this.events[n]??=[]).push(f)}fire(n){for(const f of this.events[n]||[])f()}}
 const elements={},ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element())},window:{addEventListener(){}},OcrPagePreview:{create:()=>({clear(){}})},fetch(){fetches++;throw Error('fetch forbidden')},memoryRequest:path=>new Promise((resolve,reject)=>requests.push({path,resolve,reject}))});
 vm.runInContext(script,ctx);vm.runInContext("json=memoryRequest;el('case').value='SYNTHETIC';el('run').value='OCR-A';el('task').value='TASK';el('task-status').textContent=JSON.stringify({status:'failed',marker:'OLD_RESULT'})",ctx);
 return {elements,requests,fetches:()=>fetches,query:()=>elements['check-task'].onclick()};
}
const result=status=>({caseId:'SYNTHETIC',taskId:'TASK',status,...(status==='succeeded'?{runId:'OCR-B'}:{})});
function waiting(s){assert.match(s.elements['task-status'].textContent,/正在查询，结果尚未返回/);assert.doesNotMatch(s.elements['task-status'].textContent,/OLD_RESULT/);assert.equal(s.fetches(),0)}
for(const outcome of ['succeeded','running_or_unknown','failure'])test(`current ${outcome}: pending replaces old result without polling`,async()=>{
 const s=setup(),p=s.query();waiting(s);assert.equal(s.requests.length,1);await new Promise(r=>setImmediate(r));waiting(s);assert.equal(s.requests.length,1);
 if(outcome==='failure')s.requests[0].reject(Error('synthetic query failure'));else s.requests[0].resolve(result(outcome));await p;
 assert.doesNotMatch(s.elements['task-status'].textContent,/正在查询/);
 if(outcome==='failure')assert.match(s.elements['task-status'].textContent,/synthetic query failure.*不得据此重试/);else assert.equal(JSON.parse(s.elements['task-status'].textContent).status,outcome);
 assert.equal(s.requests.length,1);assert.equal(s.fetches(),0);
});
for(const outcome of ['success','failure'])test(`older ${outcome} cannot replace newer pending or final query`,async()=>{
 const s=setup(),a=s.query(),b=s.query();waiting(s);assert.equal(s.requests.length,2);
 if(outcome==='success')s.requests[0].resolve(result('failed'));else s.requests[0].reject(Error('old failure'));await a;waiting(s);
 s.requests[1].resolve(result('running_or_unknown'));await b;assert.equal(JSON.parse(s.elements['task-status'].textContent).status,'running_or_unknown');assert.equal(s.requests.length,2);assert.equal(s.fetches(),0);
});
for(const field of ['case','run','task'])for(const outcome of ['success','failure'])test(`${field} change: stale ${outcome} leaves cleared context`,async()=>{
 const s=setup(),p=s.query();waiting(s);s.elements[field].value='OTHER';s.elements[field].fire('input');assert.equal(s.elements['task-status'].textContent,'');
 if(outcome==='success')s.requests[0].resolve(result('succeeded'));else s.requests[0].reject(Error('old failure'));await p;
 assert.equal(s.elements['task-status'].textContent,'');assert.equal(s.elements.run.value,field==='run'?'OTHER':'OCR-A');assert.equal(s.requests.length,1);assert.equal(s.fetches(),0);
});

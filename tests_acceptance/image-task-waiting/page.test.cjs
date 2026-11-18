// Actual page query callback, in-memory Promise seam; no network/application/media.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/image_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 const requests=[];let fetches=0;
 class Element{constructor(){this.value='';this.textContent='';this.events={};this.children=[]}setAttribute(){}append(...v){this.children.push(...v)}replaceChildren(){this.children=[]}addEventListener(n,f){(this.events[n]??=[]).push(f)}fire(n){this['on'+n]?.();for(const f of this.events[n]||[])f()}}
 const elements={},ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener(){}},OcrPagePreview:{create:()=>({clear(){}})},fetch(){fetches++;throw Error('fetch forbidden')},memoryRequest:path=>new Promise((resolve,reject)=>requests.push({path,resolve,reject}))});
 vm.runInContext(script,ctx);vm.runInContext("json=memoryRequest;el('case').value='SYNTHETIC';el('run').value='OCR-A';el('task').value='TASK';el('task-status').textContent=JSON.stringify({status:'failed',marker:'OLD_RESULT'})",ctx);
 return {elements,requests,read:code=>vm.runInContext(code,ctx),fetches:()=>fetches,query:()=>elements['check-task'].onclick()};
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
for(const outcome of ['success','failure'])test(`newer query finishes first; older ${outcome} leaves final display intact`,async()=>{
 const s=setup(),a=s.query(),b=s.query();s.requests[1].resolve(result('failed'));await b;const final=s.elements['task-status'].textContent;
 if(outcome==='success')s.requests[0].resolve(result('running_or_unknown'));else s.requests[0].reject(Error('old failure'));await a;
 assert.equal(s.elements['task-status'].textContent,final);assert.equal(JSON.parse(final).status,'failed');assert.equal(s.requests.length,2);assert.equal(s.fetches(),0);
});

for(const outcome of ['success','failure'])test('draft input invalidates waiting feedback / '+outcome,async()=>{
 const s=setup();s.read("state={caseId:'SYNTHETIC',runId:'OCR-A',revision:0,reviews:[],initial:{candidate:{source:{pdf_page_1based:1,printed_page:null},recognizer:{name:'synthetic'},text_lines:[{line_index:0,text:'synthetic',bbox:[0,0,10,10]}]}}};context='SYNTHETIC';render()");
 const p=s.query();waiting(s);const input=s.elements.lines.children[0].children[2];input.value='unsaved new input';input.fire('input');
 assert.match(s.elements['task-status'].textContent,/输入已变化/);assert.doesNotMatch(s.elements['task-status'].textContent,/正在查询，结果尚未返回/);
 if(outcome==='success')s.requests[0].resolve(result('succeeded'));else s.requests[0].reject(Error('old query failure'));await p;
 assert.match(s.elements['task-status'].textContent,/输入已变化/);assert.equal(s.elements.lines.children[0].children[2].value,'unsaved new input');assert.equal(s.read('dirty'),true);assert.equal(s.elements.run.value,'OCR-A');assert.equal(s.requests.length,1);assert.equal(s.fetches(),0);
});

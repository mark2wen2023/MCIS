// New ordinary synthetic successful-save tests. DOM/HTTP doubles, not a browser or OCR.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/image_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 class Element{constructor(){this.value='';this.textContent='';this.children=[];}addEventListener(name,fn){(this.events??={})[name]=fn;}setAttribute(){}removeAttribute(){}load(){}pause(){}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},events={};const releases=[],failures=[];let requests=0;
 const ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener:(name,fn)=>events[name]=fn},OcrPagePreview:{create:()=>({clear(){},select(){throw Error('preview not exercised')}})},confirm:()=>false,fetch:async()=>{requests++;const prior=JSON.parse(vm.runInContext('JSON.stringify(state)',ctx));return new Promise((resolve,reject)=>{failures.push(()=>reject(Error("synthetic transport failure")));releases.push(()=>resolve({ok:true,json:async()=>({caseId:prior.caseId,taskId:'TASK',status:'succeeded',runId:'OCR-new'})}))})}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'OCR-fixture',revision:0,initial:{candidate:{source:{pdf_page_1based:1,printed_page:null},recognizer:{pipeline:'synthetic'},text_lines:[{line_index:0,text:'synthetic',bbox:[0,0,10,10]},{line_index:1,text:'other',bbox:[0,10,10,20]}]}},reviews:[]};context='SYNTHETIC';el('task').value='TASK';el('case').value=context;el('run').value=state.runId;render();`,ctx);
 return {ctx,elements,boxes:elements.lines.children,release:(i=0)=>releases[i](),fail:(i=0)=>failures[i](),requests:()=>requests,warning:()=>{let warned=false;events.beforeunload({preventDefault(){warned=true}});return warned;}};
}
function change(row,text){row.children[2].value=text;row.children[2].oninput();row.children[4].value='synthetic correction';row.children[4].oninput();}
test('task query retains new draft and run',async()=>{
 const s=setup(),p=s.elements['check-task'].onclick();change(s.boxes[0],'new draft');s.release();await p;assert.equal(s.elements.run.value,'OCR-fixture');assert.equal(s.warning(),true);
});
for(const field of ['case','run','task'])test('task query ignores away and back '+field,async()=>{
 const s=setup(),p=s.elements['check-task'].onclick(),old=s.elements[field].value;s.elements[field].value='OTHER';s.elements[field].events?.input?.();s.elements[field].value=old;s.elements[field].events?.input?.();s.release();await p;assert.equal(s.elements.run.value,'OCR-fixture');
});
test('older task query cannot overtake newer pending query',async()=>{
 const s=setup(),a=s.elements['check-task'].onclick(),b=s.elements['check-task'].onclick();s.release(0);await a;assert.equal(s.elements.run.value,'OCR-fixture');s.release(1);await b;assert.equal(s.elements.run.value,'OCR-new');
});
test('unchanged task query displays succeeded run',async()=>{
 const s=setup(),p=s.elements['check-task'].onclick();s.release();await p;assert.equal(s.elements.run.value,'OCR-new');assert.equal(s.requests(),1);
});

test('task query late transport error leaves current status',async()=>{
 const s=setup();vm.runInContext("el('task-status').textContent='current context'",s.ctx);const p=s.elements['check-task'].onclick();s.elements.case.value='OTHER';s.elements.case.events.input();s.elements['task-status'].textContent='current context';s.fail();await p;assert.equal(s.elements['task-status'].textContent,'current context');assert.equal(s.requests(),1);
});
test('task query current transport error is explicit without retry',async()=>{
 const s=setup(),p=s.elements['check-task'].onclick();s.fail();await p;assert.match(s.elements['task-status'].textContent,/不得据此重试/);assert.equal(s.elements.run.value,'OCR-fixture');assert.equal(s.requests(),1);
});

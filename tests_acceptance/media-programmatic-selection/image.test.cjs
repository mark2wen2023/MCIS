// New ordinary synthetic successful-save tests. DOM/HTTP doubles, not a browser or OCR.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/image_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 class Element{constructor(){this.value='';this.textContent='';this.children=[];}addEventListener(name,fn){(this.events??={})[name]=fn;}setAttribute(){}removeAttribute(){}load(){}pause(){}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},events={};let release,requests=0;
 const ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener:(name,fn)=>events[name]=fn},OcrPagePreview:{create:()=>({clear(){},select(){throw Error('preview not exercised')}})},confirm:()=>false,fetch:async()=>{requests++;const prior=JSON.parse(vm.runInContext('JSON.stringify(state)',ctx));return new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>prior})})}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'OCR-fixture',revision:0,initial:{candidate:{source:{pdf_page_1based:1,printed_page:null},recognizer:{pipeline:'synthetic'},text_lines:[{line_index:0,text:'synthetic',bbox:[0,0,10,10]},{line_index:1,text:'other',bbox:[0,10,10,20]}]}},reviews:[]};context='SYNTHETIC';el('case').value=context;el('run').value=state.runId;render();`,ctx);
 return {ctx,elements,boxes:elements.lines.children,release:()=>release(),requests:()=>requests,warning:()=>{let warned=false;events.beforeunload({preventDefault(){warned=true}});return warned;}};
}
function change(row,text){row.children[2].value=text;row.children[2].oninput();row.children[4].value='synthetic correction';row.children[4].oninput();}
test('image task selection invalidates pending reread even with same run',async()=>{
 const s=setup(),row=s.boxes[0],p=s.elements.load.onclick();vm.runInContext("el('task').value='TASK';showTask({caseId:'SYNTHETIC',taskId:'TASK',status:'succeeded',runId:'OCR-fixture'},'SYNTHETIC','TASK');",s.ctx);s.release();await p;assert.equal(s.elements.lines.children[0],row);assert.match(s.elements.status.textContent,/读取期间/);assert.equal(s.requests(),1);
});

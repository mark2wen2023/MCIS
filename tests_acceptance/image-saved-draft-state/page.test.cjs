// New ordinary synthetic successful-save tests. DOM/HTTP doubles, not a browser or OCR.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/image_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 class Element{constructor(){this.value='';this.textContent='';this.children=[];}addEventListener(){}setAttribute(){}removeAttribute(){}load(){}pause(){}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},events={};let release,requests=0;
 const ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener:(name,fn)=>events[name]=fn},OcrPagePreview:{create:()=>({clear(){},select(){throw Error('preview not exercised')}})},confirm:()=>false,fetch:async(path,options)=>{requests++;const body=JSON.parse(options.body),prior=JSON.parse(vm.runInContext('JSON.stringify(state)',ctx));return new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>({...prior,revision:prior.revision+1,reviews:[...prior.reviews,body]})})})}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'OCR-fixture',revision:0,initial:{candidate:{source:{pdf_page_1based:1,printed_page:null},recognizer:{pipeline:'synthetic'},text_lines:[{line_index:0,text:'synthetic',bbox:[0,0,10,10]},{line_index:1,text:'other',bbox:[0,10,10,20]}]}},reviews:[]};context='SYNTHETIC';el('case').value=context;el('run').value=state.runId;render();`,ctx);
 return {ctx,elements,boxes:elements.lines.children,release:()=>release(),requests:()=>requests,warning:()=>{let warned=false;events.beforeunload({preventDefault(){warned=true}});return warned;}};
}
function change(row,text){row.children[2].value=text;row.children[2].oninput();row.children[4].value='synthetic correction';row.children[4].oninput();}
test('successful last draft save clears unsaved warning and permits reread',async()=>{
 const s=setup(),row=s.boxes[0];change(row,'saved synthetic');assert.equal(s.warning(),true);
 const saving=row.children[5].onclick();s.release();await saving;
 assert.match(s.elements.status.textContent,/本行已保存/);assert.equal(s.warning(),false);assert.equal(vm.runInContext('reset()',s.ctx),true);assert.equal(s.requests(),1);
});
test('saving one line keeps other draft warning until both are saved',async()=>{
 const s=setup();change(s.boxes[0],'first');change(s.boxes[1],'second');
 let saving=s.boxes[0].children[5].onclick();s.release();await saving;
 assert.equal(s.warning(),true);assert.equal(s.boxes[1].children[2].value,'second');
 saving=s.boxes[1].children[5].onclick();s.release();await saving;
 assert.equal(s.warning(),false);assert.equal(s.requests(),2);assert.equal(vm.runInContext('state.reviews.length',s.ctx),2);
});
test('edit during successful pending save remains unsaved without automatic retry',async()=>{
 const s=setup(),row=s.boxes[0];change(row,'submitted');const saving=row.children[5].onclick();
 change(row,'later unsaved');s.release();await saving;
 assert.equal(row.children[2].value,'later unsaved');assert.equal(s.warning(),true);assert.equal(s.requests(),1);
 assert.equal(vm.runInContext('state.revision',s.ctx),0);assert.match(s.elements.status.textContent,/保存结果未知/);
});

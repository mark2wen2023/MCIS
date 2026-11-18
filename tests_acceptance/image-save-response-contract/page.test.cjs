// New ordinary synthetic successful-save tests. DOM/HTTP doubles, not a browser or OCR.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/image_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(mutate=x=>x){
 class Element{constructor(){this.value='';this.textContent='';this.children=[];}addEventListener(name,fn){(this.events??={})[name]=fn;}setAttribute(){}removeAttribute(){}load(){}pause(){}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},events={};let release,requests=0;
 const ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener:(name,fn)=>events[name]=fn},OcrPagePreview:{create:()=>({clear(){},select(){throw Error('preview not exercised')}})},confirm:()=>false,fetch:async(path,options)=>{requests++;const body=JSON.parse(options.body),prior=JSON.parse(vm.runInContext('JSON.stringify(state)',ctx));return new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>mutate({...prior,revision:prior.revision+1,reviews:[...prior.reviews,body]})})})}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'OCR-fixture',revision:1,initial:{candidate:{source:{pdf_page_1based:1,printed_page:null},recognizer:{pipeline:'synthetic'},text_lines:[{line_index:0,text:'synthetic',bbox:[0,0,10,10]},{line_index:1,text:'other',bbox:[0,10,10,20]}]}},reviews:[{lineIndex:1,text:'earlier saved text',decision:'pending',reason:'synthetic prior revision'}]};context='SYNTHETIC';el('case').value=context;el('run').value=state.runId;render();`,ctx);
 return {ctx,elements,boxes:elements.lines.children,release:()=>release(),requests:()=>requests,warning:()=>{let warned=false;events.beforeunload({preventDefault(){warned=true}});return warned;}};
}
function change(row,text){row.children[2].value=text;row.children[2].oninput();row.children[4].value='synthetic correction';row.children[4].oninput();}
for(const [name,mutate] of [
 ['missing prior review',d=>({...d,reviews:d.reviews.slice(-1)})],
 ['different initial source',d=>({...d,initial:{...d.initial,candidate:{...d.initial.candidate,source:{...d.initial.candidate.source,pdf_page_1based:2}}}})],
 ['different prior review',d=>({...d,reviews:[{...d.reviews[0],text:'unrelated prior text'},...d.reviews.slice(1)]})]
])test('image save does not claim success for '+name,async()=>{
 const s=setup(mutate),row=s.boxes[0],before=vm.runInContext('JSON.stringify(state)',s.ctx);change(row,'submitted text');const p=row.children[5].onclick();s.release();await p;assert.equal(vm.runInContext('JSON.stringify(state)',s.ctx),before);assert.equal(s.warning(),true);assert.match(s.elements.status.textContent,/未知/);const current=s.elements.lines.children[0];assert.equal(s.elements.lines.children.length,2);assert.equal(current,row);assert.equal(current.children[2].value,'submitted text');assert.equal(current.children[4].value,'synthetic correction');assert.equal(s.requests(),1);
});
test('image save preserves complete matching response',async()=>{const s=setup(),row=s.boxes[0];change(row,'submitted text');const p=row.children[5].onclick();s.release();await p;assert.equal(vm.runInContext('state.revision',s.ctx),2);assert.equal(vm.runInContext('state.reviews.length',s.ctx),2);assert.equal(s.warning(),false);assert.match(s.elements.status.textContent,/本行已保存/);});

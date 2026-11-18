// Synthetic DOM only. fetch messages are handled by real FastAPI TestClient in Python.
const assert=require('node:assert/strict'),vm=require('node:vm');
const lines=require('node:readline').createInterface({input:process.stdin})[Symbol.asyncIterator]();
async function receive(){const x=await lines.next();assert(!x.done);return JSON.parse(x.value);}
(async()=>{
 const {kind,html,manifest:m}=await receive();
 class Element{constructor(){this.value='';this.textContent='';this.children=[];}addEventListener(n,f){(this.events??={})[n]=f;}setAttribute(){}removeAttribute(){}pause(){}load(){}append(...xs){this.children.push(...xs);}replaceChildren(){this.children=[];}}
 const elements={},events={};let requests=0;
 const ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener:(n,f)=>events[n]=f},confirm:()=>false,URL:{revokeObjectURL(){}},OcrPagePreview:{create:()=>({clear(){}})},fetch:async(url,options={})=>{
  requests++;console.log(JSON.stringify({type:'request',url,options}));const r=await receive();return {ok:r.status>=200&&r.status<300,json:async()=>r.body};
 }});
 vm.runInContext(html.split('<script>')[1].split('</script>')[0],ctx);
 const run=kind==='image'?m.imageRunId:m.audioRunId;
 vm.runInContext(`el('case').value=${JSON.stringify(m.caseId)};el('run').value=${JSON.stringify(run)};`,ctx);
 await elements.load.onclick();assert.equal(vm.runInContext('state.runId',ctx),run);
 if(kind==='image'){
  for(const k of ['pdf','image','raw','candidate'])vm.runInContext(`el('${k}').value=${JSON.stringify(m.receipts[k])}`,ctx);
 }else{
  vm.runInContext(`el('audio-digest').value=${JSON.stringify(m.receipts.audio)};el('draft-digest').value=${JSON.stringify(m.receipts['audio-draft'])};`,ctx);
 }
 vm.runInContext("el('ack').checked=true",ctx);
 await elements[kind==='image'?'create':'attach'].onclick();
 const created=vm.runInContext('state.runId',ctx);assert.notEqual(created,run,elements.status.textContent);
 const initial=vm.runInContext('JSON.stringify(state.initial)',ctx);
 const parent=kind==='image'?'lines':'segments',input=kind==='image'?2:1,reason=kind==='image'?4:5,save=kind==='image'?5:7;
 for(let revision=1;revision<=2;revision++){
  const row=elements[parent].children[0];row.children[input].value='SYNTHETIC correction '+revision;row.children[input].oninput();row.children[reason].value='Synthetic contract check, not human verification';row.children[reason].oninput();
  await row.children[save].onclick();assert.equal(vm.runInContext('state.revision',ctx),revision,elements.status.textContent);assert.equal(vm.runInContext('dirty',ctx),false);
  await elements.load.onclick();assert.equal(elements[parent].children[0].children[input].value,'SYNTHETIC correction '+revision);assert.equal(vm.runInContext('JSON.stringify(state.initial)',ctx),initial);
 }
 console.log(JSON.stringify({type:'done',doc:JSON.parse(vm.runInContext('JSON.stringify(state)',ctx)),requests}));
})().catch(e=>{console.error(e.stack);process.exitCode=1;}).finally(()=>{process.stdin.destroy();});

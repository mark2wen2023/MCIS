// New ordinary synthetic successful-save tests. DOM/HTTP doubles, not a browser or ASR.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(mutate=x=>x){
 class Element{constructor(){this.value='';this.textContent='';this.children=[];}addEventListener(){}setAttribute(){}removeAttribute(){}load(){}pause(){}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},events={};let release,requests=0;
 const ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener:(name,fn)=>events[name]=fn},URL:{revokeObjectURL(){}},confirm:()=>false,fetch:async()=>{requests++;const prior=JSON.parse(vm.runInContext('JSON.stringify(state)',ctx));return new Promise(resolve=>{release=()=>resolve({ok:true,json:async()=>mutate(prior)})})}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'AR-fixture',revision:0,initial:{audio:{frames:8000,sampleRateHz:8000},machineDraft:{transcript:{segments:[{id:'s1',text:'synthetic',startMs:0,endMs:500},{id:'s2',text:'other',startMs:500,endMs:1000}],unlocatedSegments:[]}}},humanRevisions:[]};context='SYNTHETIC';el('case').value=context;el('run').value=state.runId;render();`,ctx);
 return {ctx,elements,boxes:elements.segments.children,release:()=>release(),requests:()=>requests,warning:()=>{let warned=false;events.beforeunload({preventDefault(){warned=true}});return warned;}};
}
function change(row,text){row.children[1].value=text;row.children[1].oninput();row.children[5].value='synthetic correction';row.children[5].oninput();}
const mutations=['d.initial.machineDraft.transcript=null', 'd.initial.machineDraft.transcript.segments=null', 'd.initial.machineDraft.transcript.unlocatedSegments={}', 'd.initial.machineDraft.transcript.segments=[null]', 'd.humanRevisions=[null]'];
for(const mutation of mutations)test('audio rejects render-invalid response '+mutation,async()=>{
 const s=setup(d=>{new Function('d',mutation)(d);return d;}),row=s.boxes[0],before=vm.runInContext('JSON.stringify(state)',s.ctx),p=s.elements.load.onclick();s.release();await p;assert.equal(vm.runInContext('JSON.stringify(state)',s.ctx),before);assert.equal(s.elements.segments.children[0],row);assert.equal(s.requests(),1);
});
test('audio valid reread still renders',async()=>{const s=setup(),row=s.boxes[0],p=s.elements.load.onclick();s.release();await p;assert.notEqual(s.elements.segments.children[0],row);assert.equal(s.requests(),1);});

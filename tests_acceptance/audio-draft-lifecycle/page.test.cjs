// Pure Node synthetic DOM/Promise tests: no HTTP, audio bytes or Python imports.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 let resolve,reject,plays=0,fetches=0;const confirms=[],listeners={};
 const pending=new Promise((a,b)=>{resolve=a;reject=b});
 class Element{
  constructor(){this.value='';this.textContent='';this.children=[];this.readyState=1;this.events={};}
  addEventListener(n,f){(this.events[n]??=[]).push(f)}
  fire(n){this['on'+n]?.({target:this});for(const f of this.events[n]||[])f({target:this})}
  setAttribute(){}removeAttribute(){}load(){}pause(){}play(){plays++;return pending}
  append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}
 }
 const elements={},ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener:(n,f)=>(listeners[n]??=[]).push(f)},URL:{revokeObjectURL(){}},confirm:message=>{confirms.push(message);return false},fetch:()=>{fetches++;throw Error('fetch forbidden')}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'AR-fixture',revision:0,initial:{audio:{frames:8000,sampleRateHz:8000},machineDraft:{transcript:{segments:[{id:'s1',text:'synthetic',startMs:0,endMs:500}],unlocatedSegments:[]}}},humanRevisions:[]};context='SYNTHETIC';el('case').value=context;el('run').value=state.runId;render();url='synthetic-object-url';`,ctx);
 return {elements,ctx,resolve,reject,confirms,read:code=>vm.runInContext(code,ctx),counts:()=>({plays,fetches}),leave(){let prevented=0;const event={returnValue:undefined,preventDefault(){prevented++}};assert.equal(listeners.beforeunload.length,1);for(const f of listeners.beforeunload)f(event);return {prevented,returnValue:event.returnValue}}};
}
function assertDraft(s){
 assert.equal(s.elements.segments.children[0].children[1].value,'unsaved synthetic text');
 assert.equal(s.read('dirty'),true);assert.equal(s.read('dirtySegments.size'),1);
 assert.equal(s.read("dirtySegments.has('s1')"),true);assert.equal(s.read('editVersion'),1);
 assert.deepEqual(s.leave(),{prevented:1,returnValue:''});
}
for(const change of ['clear','run'])for(const outcome of ['success','failure'])test(`${change}/${outcome}: pending-play edit retains dirty and cancelled replacement`,async()=>{
 const s=setup(),work=s.elements.segments.children[0].children[6].onclick();
 assert.equal(s.read('busy'),true);assert.deepEqual(s.leave(),{prevented:0,returnValue:undefined});
 const input=s.elements.segments.children[0].children[1];input.value='unsaved synthetic text';input.fire('input');assertDraft(s);
 if(change==='clear')s.elements.clear.onclick();else{s.elements.run.value='AR-other';s.elements.run.fire('input')}
 assertDraft(s);assert.equal(s.elements['play-status'].textContent,'原音未载入');
 if(outcome==='success')s.resolve();else s.reject(new Error('synthetic stale playback failure'));
 await work;assert.equal(s.read('busy'),false);assertDraft(s);
 assert.equal(s.elements['play-status'].textContent,'原音未载入');
 // After busy releases, exercise actual load callback; cancellation must precede fetch.
 await s.elements.load.onclick();assert.equal(s.confirms.length,1);assert.match(s.confirms[0],/未保存输入/);
 assertDraft(s);assert.equal(s.read('state.runId'),'AR-fixture');assert.equal(s.read('context'),'SYNTHETIC');
 assert.equal(s.elements.run.value,change==='run'?'AR-other':'AR-fixture');
 assert.deepEqual(s.counts(),{plays:1,fetches:0});
});
for(const change of ['clear','run'])test(`${change}: unedited control does not request unload warning`,async()=>{
 const s=setup(),work=s.elements.segments.children[0].children[6].onclick();
 if(change==='clear')s.elements.clear.onclick();else{s.elements.run.value='AR-other';s.elements.run.fire('input')}
 s.resolve();await work;
 assert.equal(s.read('dirty'),false);assert.equal(s.read('dirtySegments.size'),0);assert.equal(s.read('editVersion'),0);
 assert.deepEqual(s.leave(),{prevented:0,returnValue:undefined});assert.equal(s.read('canReplace()'),true);
 assert.equal(s.confirms.length,0);assert.equal(s.elements.segments.children[0].children[1].value,'synthetic');
 assert.deepEqual(s.counts(),{plays:1,fetches:0});
});

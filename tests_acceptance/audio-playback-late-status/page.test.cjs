// Pure Node DOM/media doubles. No HTTP, audio bytes, Python or browser.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 let resolve,reject,plays=0,fetches=0;const pending=new Promise((a,b)=>{resolve=a;reject=b});
 class Element{constructor(){this.value='';this.textContent='';this.children=[];this.readyState=1;this.events={};}addEventListener(n,f){(this.events[n]??=[]).push(f)}fire(n){for(const f of this.events[n]||[])f()}setAttribute(){}removeAttribute(){}load(){}pause(){}play(){plays++;return pending}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener(){}},URL:{revokeObjectURL(){}},confirm:()=>true,fetch:()=>{fetches++;throw Error('fetch forbidden in this test')}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'AR-fixture',revision:0,initial:{audio:{frames:8000,sampleRateHz:8000},machineDraft:{transcript:{segments:[{id:'s1',text:'synthetic',startMs:0,endMs:500}],unlocatedSegments:[]}}},humanRevisions:[]};context='SYNTHETIC';el('case').value=context;el('run').value=state.runId;render();url='synthetic-object-url';`,ctx);
 return {elements,ctx,resolve,reject,counts:()=>({plays,fetches})};
}
for(const change of ['case','run','clear'])for(const outcome of ['success','failure'])test(`${change}: late ${outcome} leaves current messages and draft`,async()=>{
 const s=setup(),box=s.elements.segments.children[0];box.children[1].value='retained synthetic draft';
 const work=box.children[6].onclick();assert.equal(s.counts().plays,1);
 if(change==='clear')s.elements.clear.onclick();else{s.elements[change].value='OTHER';s.elements[change].fire('input')}
 assert.equal(s.elements['play-status'].textContent,'原音未载入');s.elements.status.textContent='new context status';
 if(outcome==='success')s.resolve();else s.reject(new Error('old play failure'));
 await work;
 assert.equal(s.elements['play-status'].textContent,'原音未载入');assert.equal(s.elements.status.textContent,'new context status');
 assert.equal(s.elements.segments.children[0].children[1].value,'retained synthetic draft');
 assert.equal(vm.runInContext('stopAt',s.ctx),null);assert.deepEqual(s.counts(),{plays:1,fetches:0});
});
for(const outcome of ['success','failure'])test(`current context ${outcome} remains visible`,async()=>{
 const s=setup(),work=s.elements.segments.children[0].children[6].onclick();
 if(outcome==='success')s.resolve();else s.reject(new Error('current play failure'));await work;
 if(outcome==='success')assert.match(s.elements['play-status'].textContent,/回听片段 s1/);else assert.match(s.elements.status.textContent,/current play failure/);
 assert.deepEqual(s.counts(),{plays:1,fetches:0});
});

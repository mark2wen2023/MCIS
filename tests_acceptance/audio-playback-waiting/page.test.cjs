// Pure Node DOM/media doubles. No HTTP, audio bytes, Python or browser.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 let resolve,reject,plays=0,fetches=0;const pending=new Promise((a,b)=>{resolve=a;reject=b});
 class Element{constructor(){this.value='';this.textContent='';this.children=[];this.readyState=1;this.events={};}addEventListener(n,f){(this.events[n]??=[]).push(f)}fire(n){this['on'+n]?.();for(const f of this.events[n]||[])f()}setAttribute(){}removeAttribute(){}load(){}pause(){}play(){plays++;return pending}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener(){}},URL:{revokeObjectURL(){}},confirm:()=>true,fetch:()=>{fetches++;throw Error('fetch forbidden in this test')}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'AR-fixture',revision:0,initial:{audio:{frames:8000,sampleRateHz:8000},machineDraft:{transcript:{segments:[{id:'s1',text:'synthetic',startMs:0,endMs:500}],unlocatedSegments:[]}}},humanRevisions:[]};context='SYNTHETIC';el('case').value=context;el('run').value=state.runId;render();url='synthetic-object-url';`,ctx);
 return {elements,ctx,resolve,reject,counts:()=>({plays,fetches})};
}

function draft(s){const input=s.elements.segments.children[0].children[1];input.value='unsaved synthetic draft';input.fire('input');}
function retained(s){assert.equal(s.elements.segments.children[0].children[1].value,'unsaved synthetic draft');assert.equal(vm.runInContext('dirty',s.ctx),true);assert.deepEqual(s.counts(),{plays:1,fetches:0});}
function waiting(s){assert.match(s.elements['play-status'].textContent,/正在等待播放器响应/);assert.match(s.elements['play-status'].textContent,/s1.*0–500ms/);assert.match(s.elements['play-status'].textContent,/不等于已开始播放或已听取/);assert.equal(vm.runInContext('busy',s.ctx),true);}
for(const change of ['none','case','run','clear'])for(const outcome of ['success','failure'])test(change+' / '+outcome+': waiting and settlement are scoped without retry',async()=>{
 const s=setup(),play=s.elements.segments.children[0].children[6];const work=play.onclick();draft(s);waiting(s);retained(s);
 await play.onclick();waiting(s);assert.equal(s.counts().plays,1);
 await new Promise(resolve=>setImmediate(resolve));waiting(s);assert.equal(s.counts().plays,1);
 if(change==='clear')s.elements.clear.onclick();else if(change!=='none'){s.elements[change].value='OTHER';s.elements[change].fire('input')}
 if(change!=='none'){assert.equal(s.elements['play-status'].textContent,'原音未载入');s.elements.status.textContent='current context';}
 if(outcome==='success')s.resolve();else s.reject(Error('synthetic play failure'));
 await work;await new Promise(resolve=>setImmediate(resolve));assert.equal(vm.runInContext('busy',s.ctx),false);retained(s);
 if(change!=='none'){assert.equal(s.elements['play-status'].textContent,'原音未载入');assert.equal(s.elements.status.textContent,'current context');}
 else if(outcome==='success'){assert.match(s.elements['play-status'].textContent,/回听片段 s1/);assert.doesNotMatch(s.elements['play-status'].textContent,/正在等待/);}
 else {assert.match(s.elements['play-status'].textContent,/播放器未确认开始播放/);assert.doesNotMatch(s.elements['play-status'].textContent,/正在等待/);assert.match(s.elements.status.textContent,/synthetic play failure/);}
});

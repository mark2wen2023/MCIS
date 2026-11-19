// Pure Node DOM/media doubles. No HTTP, audio bytes, Python or browser.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 let resolve,reject,plays=0,fetches=0;const pending=new Promise((a,b)=>{resolve=a;reject=b});
 class Element{constructor(){this.value='';this.textContent='';this.children=[];this.readyState=1;this.currentTime=.75;this.events={};}addEventListener(n,f){(this.events[n]??=[]).push(f)}fire(n){this['on'+n]?.();for(const f of this.events[n]||[])f()}setAttribute(){}removeAttribute(){}load(){}pause(){}play(){plays++;return pending}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener(){}},URL:{revokeObjectURL(){}},confirm:()=>true,fetch:()=>{fetches++;throw Error('fetch forbidden in this test')}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'AR-fixture',revision:0,initial:{audio:{frames:8000,sampleRateHz:8000},machineDraft:{transcript:{segments:[{id:'s1',text:'synthetic',startMs:0,endMs:500}],unlocatedSegments:[]}}},humanRevisions:[]};context='SYNTHETIC';el('case').value=context;el('run').value=state.runId;render();url='synthetic-object-url';`,ctx);
 return {elements,ctx,resolve,reject,counts:()=>({plays,fetches})};
}

function controls(s){const c=s.elements.segments.children[0].children;return {text:c[1],start:c[3],end:c[4],play:c[6]};}
for(const [start,end] of [[' ','500'],['\t','500'],['',''],['0',''],['500','100'],['0','1001']])test('unusable input '+JSON.stringify([start,end])+' does not seek or play',async()=>{
 const s=setup(),c=controls(s);c.start.value=start;c.end.value=end;c.text.value='retained';c.text.fire('input');s.resolve();
 await c.play.onclick();
 assert.equal(s.counts().plays,0);assert.equal(s.counts().fetches,0);
 assert.equal(s.elements.player.currentTime,.75);assert.equal(vm.runInContext('stopAt',s.ctx),null);
 assert.match(s.elements['play-status'].textContent,/未定位/);assert.equal(c.text.value,'retained');assert.equal(vm.runInContext('dirty',s.ctx),true);
});
test('explicit numeric zero is valid and not auto-played before the action',async()=>{
 const s=setup(),c=controls(s);c.start.value='0';c.end.value='500';assert.equal(s.counts().plays,0);s.resolve();await c.play.onclick();
 assert.equal(s.elements.player.currentTime,0);assert.equal(s.counts().plays,1);assert.match(s.elements['play-status'].textContent,/不构成已听证明/);
});
for(const change of ['unloaded','not-ready','case','run'])test(change+' prevents seek while preserving input',async()=>{
 const s=setup(),c=controls(s);c.start.value='100';c.end.value='500';
 if(change==='unloaded')s.elements.clear.onclick();
 else if(change==='not-ready')s.elements.player.readyState=0;
 else{s.elements[change].value='SYN-OTHER';s.elements[change].fire('input');}
 s.resolve();await c.play.onclick();assert.equal(s.counts().plays,0);assert.equal(s.elements.player.currentTime,.75);assert.equal(c.start.value,'100');assert.equal(s.counts().fetches,0);
 assert.match(s.elements['play-status'].textContent,/未定位/);
});

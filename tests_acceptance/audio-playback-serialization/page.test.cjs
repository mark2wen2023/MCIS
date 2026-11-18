// Pure Node DOM/media doubles. No HTTP, audio bytes, Python or browser.
const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const script=fs.readFileSync('service/mcis_service/audio_review/review.html','utf8').split('<script>')[1].split('</script>')[0];
function setup(){
 let fetches=0;const calls=[];
 class Element{constructor(){this.value='';this.textContent='';this.children=[];this.readyState=1;this.events={};}addEventListener(n,f){(this.events[n]??=[]).push(f)}fire(n){for(const f of this.events[n]||[])f()}setAttribute(){}removeAttribute(){}load(){}pause(){}play(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});calls.push({resolve,reject,time:this.currentTime});return promise}append(...xs){this.children.push(...xs)}replaceChildren(){this.children=[]}}
 const elements={},ctx=vm.createContext({document:{getElementById:id=>elements[id]??(elements[id]=new Element()),createElement:()=>new Element()},window:{addEventListener(){}},URL:{revokeObjectURL(){}},confirm:()=>true,fetch:()=>{fetches++;throw Error('fetch forbidden in this test')}});
 vm.runInContext(script,ctx);
 vm.runInContext(`state={caseId:'SYNTHETIC',runId:'AR-fixture',revision:0,initial:{audio:{frames:8000,sampleRateHz:8000},machineDraft:{transcript:{segments:[{id:'s1',text:'synthetic A',startMs:100,endMs:400},{id:'s2',text:'synthetic B',startMs:600,endMs:900}],unlocatedSegments:[]}}},humanRevisions:[]};context='SYNTHETIC';el('case').value=context;el('run').value=state.runId;render();url='synthetic-object-url';`,ctx);
 return {elements,ctx,calls,fetches:()=>fetches};
}
for(const outcome of ['success','failure'])test(`A ${outcome}: pending B is ignored, explicit later B starts`,async()=>{
 const s=setup(),[a,b]=s.elements.segments.children,player=s.elements.player;
 a.children[1].value='A unsaved';b.children[1].value='B unsaved';
 const aWork=a.children[6].onclick();
 assert.equal(s.calls.length,1);assert.equal(s.calls[0].time,0.1);
 assert.equal(vm.runInContext('stopAt',s.ctx),0.4);assert.equal(vm.runInContext('busy',s.ctx),true);
 const previousMessage=s.elements['play-status'].textContent;
 await b.children[6].onclick();
 assert.equal(s.calls.length,1,'pending B must not dispatch');assert.equal(player.currentTime,0.1);
 assert.equal(vm.runInContext('stopAt',s.ctx),0.4);assert.equal(s.elements['play-status'].textContent,previousMessage);
 if(outcome==='success')s.calls[0].resolve();else s.calls[0].reject(new Error('synthetic A playback failure'));
 await aWork;await new Promise(resolve=>setImmediate(resolve));
 assert.equal(vm.runInContext('busy',s.ctx),false);assert.equal(s.calls.length,1,'ignored B must not replay after A settles');
 if(outcome==='success')assert.equal(s.elements['play-status'].textContent,'回听片段 s1，输入范围 100–400ms；不构成已听证明。');
 else {assert.match(s.elements.status.textContent,/synthetic A playback failure/);assert.match(s.elements['play-status'].textContent,/播放器未确认开始播放/)}
 const bWork=b.children[6].onclick();
 assert.equal(s.calls.length,2,'only explicit second B click starts playback');assert.equal(s.calls[1].time,0.6);
 assert.equal(player.currentTime,0.6);assert.equal(vm.runInContext('stopAt',s.ctx),0.9);
 s.calls[1].resolve();await bWork;
 assert.equal(s.elements['play-status'].textContent,'回听片段 s2，输入范围 600–900ms；不构成已听证明。');
 assert.equal(vm.runInContext('busy',s.ctx),false);assert.equal(s.calls.length,2);assert.equal(s.fetches(),0);
 assert.equal(s.elements.segments.children[0].children[1].value,'A unsaved');
 assert.equal(s.elements.segments.children[1].children[1].value,'B unsaved');
});

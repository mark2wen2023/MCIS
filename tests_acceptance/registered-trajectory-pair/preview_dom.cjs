// Handwritten DOM checks of the delivered preview, NOT browser acceptance.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const displayOnly=process.argv[2]==='--display-only';
const html=fs.readFileSync(process.argv[displayOnly?3:2],'utf8');
class E{constructor(){this.children=[];this.attrs={};this.textContent='';this.value='';this.disabled=false;this.classList={toggle(){}};}appendChild(e){this.children.push(e);return e;}replaceChildren(){this.children=[];}setAttribute(k,v){this.attrs[k]=String(v);}getAttribute(k){return this.attrs[k]??null;}}
const nodes=Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(m=>[m[1],new E()]));
const deny=()=>{throw Error('Unexpected IO');};const ctx={document:{getElementById:id=>{assert(nodes[id],id);return nodes[id];},createElement:()=>new E(),createElementNS:()=>new E()},setTimeout,fetch:deny,XMLHttpRequest:deny};
for(const k of ['location','localStorage','sessionStorage'])Object.defineProperty(ctx,k,{get:deny});
for(const s of html.matchAll(/<script>([\s\S]*?)<\/script>/g))vm.runInNewContext(s[1],ctx);
const count=()=>nodes['preview-count'].textContent,markers=()=>nodes.map.children.filter(n=>n.attrs['data-current']);
(async()=>{
 for(let i=0;i<20;i++){nodes['preview-slider'].value=String(i%(displayOnly?2:4));nodes['preview-slider'].oninput();}assert.equal(count(),''); // fake DOM doesn't parse initial text
 nodes['preview-slider'].value='0';nodes['preview-slider'].oninput();await nodes['registered-load'].onclick();assert.equal(count(),'模拟查询次数：1');assert.equal(markers().length,2);
 nodes['source-b'].onclick();assert.equal(nodes.correction.textContent,'12 s');assert.match(nodes.quality.textContent,displayOnly?/契约记录点/:/已存插值/);assert.equal(nodes.pointer.textContent,displayOnly?'/points/12':'/points/2');
 nodes['preview-slider'].value='1';nodes['preview-slider'].oninput();assert.equal(markers().length,0);assert.equal(nodes.ref.textContent,'—');await nodes['registered-load'].onclick();assert.equal(markers().length,displayOnly?0:1);
 if(!displayOnly){nodes['preview-slider'].value='3';nodes['preview-slider'].oninput();await nodes['registered-load'].onclick();assert.equal(markers().length,0);assert.match(nodes['state-note'].textContent,/无精确行/);}
 if(displayOnly){nodes['source-a'].onclick();assert.equal(nodes.pointer.textContent,'/sampling/missingIntervals/1');assert(nodes['source-b'].disabled);}
 await nodes['preview-late'].onclick();assert.equal(markers().length,0);assert.equal(nodes['registered-case'].textContent,'未选案件');assert.match(nodes['preview-event'].textContent,/被忽略/);
 nodes['preview-reset'].onclick();assert.equal(markers().length,0);assert.equal(count(),displayOnly?'模拟查询次数：3':'模拟查询次数：4');
 console.log('PASS preview finite frames, local staging/query count, clear, late invalidation/reset; fake DOM only');
})().catch(e=>{console.error(e);process.exitCode=1;});

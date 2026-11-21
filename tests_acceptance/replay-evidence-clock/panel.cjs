// Execute only generated panel JS with hand-written DOM. No browser, network or maps.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8');
const data=html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const code=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
class Node {constructor(){this.children=[];this.textContent='';this.value='';this.attrs={};}appendChild(n){this.children.push(n);}replaceChildren(){this.children=[];}setAttribute(k,v){this.attrs[k]=v;}}
const nodes=Object.fromEntries(['data','time','prev','next','clock','plot','vessels','events','excluded','detail'].map(k=>[k,new Node()]));nodes.data.textContent=data;
vm.runInNewContext(code,{document:{getElementById:id=>{assert(nodes[id],id);return nodes[id];},createElement:()=>new Node(),createElementNS:()=>new Node()}});
const frames=JSON.parse(data).frames;
function at(t){nodes.time.value=String(frames.findIndex(f=>f.relativeSeconds===t));assert.notEqual(nodes.time.value,'-1');nodes.time.onchange();}
at(100);assert.equal(nodes.plot.children.length,2);assert.equal(nodes.events.children.length,2);nodes.events.children[1].onclick();let selected=JSON.parse(nodes.detail.textContent);assert.equal(selected.time.correctionSeconds,7);assert.equal(selected.associatedTrack.records[0].rawRecord.pointId,'A-t100');
at(80);assert.equal(nodes.plot.children.length,1);assert.equal(nodes.detail.textContent,'请选择此时点记录；未沿用上一时点定位。');assert.match(nodes.vessels.children[0].children[1].textContent,/禁止跨缺口/);
at(124.25);assert.equal(nodes.plot.children.length,0);assert.match(nodes.excluded.children[0].textContent,/不参与同步/);
at(20);nodes.vessels.children[1].children[3].onclick();selected=JSON.parse(nodes.detail.textContent);assert.equal(selected.rawRecord.pointId,'B-t20');assert.equal(selected.rawRecord.position.kind,'interpolated');assert.equal(selected.rawRecord.time.sourceUtc,'2026-02-01T12:00:08.000Z');assert.equal(selected.rawRecord.time.correctionSeconds,12);
for(const t of [60,100,121,127.5]){at(t);assert.match(nodes.vessels.children[0].children[1].textContent,/艏向：未知/);}
console.log('PASS actual panel JS: same-clock selection, raw record, gaps, old detail cleared, device exclusion, t20 quality; synthetic DOM only');

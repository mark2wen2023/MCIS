// Actual new workbench script in a hand-written DOM. NOT browser/pixel validation.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8');
const raw=html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const js=html.match(/<script>([\s\S]*?)<\/script>/)[1],data=JSON.parse(raw);
class E{constructor(){this.children=[];this.attrs={};this.textContent='';this.value='';this.disabled=false;this.open=false;this.classList={toggle:(n,v)=>this.attrs[n]=v};}appendChild(n){this.children.push(n);return n;}replaceChildren(){this.children=[];}setAttribute(k,v){if(['x','y','x1','y1','x2','y2','cx','cy','r','width','height'].includes(k))assert(Number.isFinite(Number(v)),`non-finite SVG ${k}`);this.attrs[k]=String(v);}getAttribute(k){return this.attrs[k]??null;}focus(){this.focused=true;}}
function mount(input){
const nodes=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new E()]));nodes.data.textContent=JSON.stringify(input);
vm.runInNewContext(js,{document:{getElementById:id=>{assert(nodes[id],id);return nodes[id];},createElement:()=>new E(),createElementNS:()=>new E()}});
return nodes;
}
const nodes=mount(data);
const at=t=>{nodes.time.value=String(data.frames.findIndex(f=>f.relativeSeconds===t));assert.notEqual(nodes.time.value,'-1');nodes.time.onchange();};
const markers=()=>nodes.map.children.filter(n=>n.attrs['data-current']);
assert.equal(nodes['record-id'].textContent,'A-t100');assert.equal(markers().length,2);assert.match(nodes.warning.textContent,/不以航迹向代替艏向/);
at(20);assert.equal(nodes['record-id'].textContent,'—');assert(nodes['raw-open'].disabled);nodes['point-options'].children[1].onclick();assert.equal(nodes['record-id'].textContent,'B-t20');assert.equal(nodes['source-time'].textContent,'2026-02-01T12:00:08.000Z');assert.equal(nodes.correction.textContent,'+12 s');assert.equal(nodes.quality.textContent,'输入已存插值');assert.equal(JSON.parse(nodes.raw.textContent).jsonPointer,'/points/2');nodes['raw-open'].onclick();assert(nodes['raw-details'].open);assert(nodes.raw.focused);
nodes['device-known'].onclick();assert.match(nodes.clock.textContent,/T\+100s/);assert.equal(nodes['record-id'].textContent,'SYN-DEVICE-01');assert.equal(nodes.correction.textContent,'+7 s');assert.equal(nodes['aligned-time'].textContent,'2026-02-01T12:01:40.000Z');assert.equal(nodes.file.textContent,'device-records.json');
at(80);assert(nodes['source-a'].disabled);assert(!nodes['source-b'].disabled);assert.equal(markers().length,1);assert.equal(markers()[0].attrs['data-current'],'SYN-VESSEL-B');assert.equal(nodes['record-id'].textContent,'—');assert.equal(nodes['raw-details'].open,false);assert.match(nodes['state-note'].textContent,/A：缺轨/);markers()[0].onclick();assert.equal(nodes['record-id'].textContent,'B-t80');
at(124.25);assert(nodes['source-a'].disabled);assert(nodes['source-b'].disabled);assert.equal(markers().length,0);assert.equal(nodes['point-options'].children.length,0);assert.match(nodes['state-note'].textContent,/B：此时点无精确观测/);const clock=nodes.clock.textContent;nodes['device-unknown'].onclick();assert.equal(nodes.clock.textContent,clock);assert.equal(markers().length,0);assert.equal(nodes['aligned-time'].textContent,'不参与同步');assert.equal(nodes.correction.textContent,'未知');assert.equal(nodes['record-id'].textContent,'SYN-DEVICE-02');assert.deepEqual(nodes.timeline.children.filter(n=>n.attrs['data-device']).map(n=>n.attrs['data-device']),['SYN-DEVICE-01']);
for(const t of [60,100,121,127.5]){at(t);nodes['point-options'].children[0].onclick();assert.equal(JSON.parse(nodes.raw.textContent).rawRecord.headingDeg.value,null);assert.match(nodes.warning.textContent,/不以航迹向代替艏向/);}
const history=nodes.map.children.filter(n=>n.attrs['data-history']==='SYN-VESSEL-A');assert(history.length>0);for(const line of history){const a=Number(line.attrs['data-from']),b=Number(line.attrs['data-to']);assert(![[60,100],[121,127.5]].some(([lo,hi])=>a<hi&&b>lo));}assert(history.some(n=>n.attrs['stroke-dasharray']==='4 4'));assert(nodes.timeline.children.some(n=>n.attrs['data-gap']==='121:127.5'));
at(0);assert(nodes.prev.disabled);nodes.next.onclick();assert.notEqual(nodes.time.value,'0');nodes.prev.onclick();assert.equal(nodes.time.value,'0');at(220);assert(nodes.next.disabled);
nodes['nav-toggle'].onclick();assert.equal(nodes['nav-toggle'].attrs['aria-expanded'],'true');assert.equal(nodes.navigation.attrs.open,true);nodes['nav-toggle'].onclick();assert.equal(nodes.navigation.attrs.open,false);
console.log('PASS actual workbench JS: exact provenance, clocks, input quality, stale clearing, markers, both gaps, history, unknown device, keyboard-equivalent controls and nav toggle; synthetic DOM only');

// Run the actual production script with independent synthetic coordinate cases.
// No raw fixture is changed; only copies of the display input are used here.
assert.deepEqual(data.bounds.latDeg,[-40,-40]);
for(const f of data.frames){at(f.relativeSeconds);for(const m of markers())assert.equal(Number(m.attrs.cy),195);}
function geometry(name,bounds,points,expected,single=false){
 const input=JSON.parse(raw);input.bounds=bounds;
 for(const frame of input.frames)for(const [i,v] of frame.vessels.entries())if(v.position?.value)v.position.value={...points[i]};
 for(const [i,h] of input.history.entries())for(const p of h.points)if(p.position?.value)p.position.value={...points[i]};
 if(single){input.history=[];for(const frame of input.frames){frame.vessels[1].position=null;frame.vessels[1].records=[];}}
 const rendered=mount(input).map.children.filter(n=>n.attrs['data-current']);
 assert.equal(rendered.length,expected.length,name);
 assert.deepEqual(rendered.map(n=>[Number(n.attrs.cx),Number(n.attrs.cy)]),expected,name);
}
geometry('horizontal',{lonDeg:[10,30],latDeg:[5,5]},[{lonDeg:10,latDeg:5},{lonDeg:30,latDeg:5}],[[36,195],[774,195]]);
geometry('vertical',{lonDeg:[10,10],latDeg:[0,20]},[{lonDeg:10,latDeg:0},{lonDeg:10,latDeg:20}],[[405,320],[405,70]]);
geometry('single location',{lonDeg:[10,10],latDeg:[5,5]},[{lonDeg:10,latDeg:5},{lonDeg:10,latDeg:5}],[[405,195],[405,195]]);
geometry('single point',{lonDeg:[10,10],latDeg:[5,5]},[{lonDeg:10,latDeg:5},{lonDeg:10,latDeg:5}],[[405,195]],true);
geometry('non-degenerate',{lonDeg:[10,30],latDeg:[0,20]},[{lonDeg:10,latDeg:0},{lonDeg:30,latDeg:20}],[[36,320],[774,70]]);
for(const value of [NaN,Infinity,-Infinity])assert.throws(()=>new E().setAttribute('cy',value),/non-finite SVG/);
console.log('PASS SVG finite attributes: frozen horizontal frames, horizontal/vertical/single-location/non-degenerate exact coordinates; synthetic DOM only');

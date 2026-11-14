const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const html = fs.readFileSync(process.argv[2], 'utf8');
const template = JSON.parse(html.match(/<script id="worksheet-template" type="application\/json">(.*?)<\/script>/s)[1]);
const script = [...html.matchAll(/<script>(.*?)<\/script>/sg)].at(-1)[1];
const nodes = {};
for (const id of ['import-file','apply-import','cancel-import','clear-notes','confirm-clear','import-status']) nodes[id] = {addEventListener(n,f){this[n]=f;}};
const fields = template.items.map(() => {const boxes=Array.from({length:3},()=>({checked:false})), area={value:'existing'};return {boxes,area,querySelectorAll:()=>boxes,querySelector:()=>area};});
const doc = {getElementById:id=>id==='worksheet-template'?{textContent:JSON.stringify(template)}:nodes[id],querySelectorAll:()=>fields,addEventListener(n,f){this[n]=f;},dispatchEvent(e){this[e.type]({target:this});}};
vm.runInNewContext(script,{document:doc,Event,TextDecoder});
const picker=nodes['import-file'], status=nodes['import-status'];
const snapshot=()=>JSON.stringify(fields.map(f=>[f.area.value,...f.boxes.map(b=>b.checked)]));
async function select(raw){const bytes=Buffer.from(raw);picker.files=[{size:bytes.length,arrayBuffer:async()=>bytes}];await picker.change();}
const data=structuredClone(template);
data.items.forEach((r,i)=>{r.note=`原文 ${i} </script> 😀\n`;r.timeAssociationNeedsCheck=true;});
(async()=>{
 const before=snapshot();
 await select(JSON.stringify(data)); assert.equal(snapshot(),before); assert.equal(nodes['apply-import'].disabled,false);
 nodes['cancel-import'].click(); nodes['apply-import'].click(); assert.equal(snapshot(),before);
 await select(JSON.stringify(data)); nodes['apply-import'].click(); assert.equal(fields[0].area.value,data.items[0].note);
 const restored=snapshot(); await select(JSON.stringify(data)); nodes['apply-import'].click(); assert.equal(snapshot(),restored);
 const invalid=[];
 for(const field of ['corpusSha256','predictionsSha256','status']) {const x=structuredClone(data);x[field]='invalid';invalid.push(JSON.stringify(x));}
 const x=structuredClone(data);x.items[0].note=''; invalid.push(JSON.stringify(x));
 const y=structuredClone(data);y.items[1]=y.items[0]; invalid.push(JSON.stringify(y));
 invalid.push(JSON.stringify(data).replace('"schemaVersion":1','"schemaVersion":1.0'),JSON.stringify(data).replace('"schemaVersion":1','"schemaVersion":1,"schemaVersion":1'),JSON.stringify(data).replace('"schemaVersion":1','"schemaVersion":true'),JSON.stringify({...data,author:'someone'}),'not JSON',JSON.stringify(data).replace('"note":','"note":"first","note":'));
 for(const raw of invalid){await select(raw);assert.equal(nodes['apply-import'].disabled,true);nodes['apply-import'].click();assert.equal(snapshot(),restored);assert.match(status.textContent,/拒绝/);}
 await select(JSON.stringify(data)); doc.input({target:fields[0].area}); assert.equal(nodes['apply-import'].disabled,true);
 let resolve; picker.files=[{size:10,arrayBuffer:()=>new Promise(r=>resolve=r)}]; const reading=picker.change(); nodes['cancel-import'].click(); resolve(Buffer.from(JSON.stringify(data)));await reading;assert.equal(nodes['apply-import'].disabled,true);assert.equal(snapshot(),restored);
 picker.files=[{size:10,arrayBuffer:async()=>{throw Error('read')}}];await picker.change();assert.equal(snapshot(),restored);assert.match(status.textContent,/拒绝/);
 picker.files=[{size:4*1024*1024+1,arrayBuffer:()=>{throw Error('must not read')}}];await picker.change();assert.equal(snapshot(),restored);
 nodes['clear-notes'].click();nodes['cancel-import'].click();nodes['confirm-clear'].click();assert.equal(snapshot(),restored);
 nodes['clear-notes'].click();nodes['confirm-clear'].click();assert.ok(fields.every(f=>f.area.value===''&&f.boxes.every(b=>!b.checked)));
 picker.files=[];await picker.change();assert.match(status.textContent,/取消/);
 await select(JSON.stringify({...data,items:[...data.items].reverse()}));nodes['apply-import'].click();assert.equal(snapshot(),restored);
 console.log('restore checks passed: binding/strict schema/duplicates/repeated/cancel/clear/read race/errors');
})().catch(e=>{console.error(e);process.exitCode=1;});

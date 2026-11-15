// Synthetic execution of exact parent callbacks, not a browser test.
const {execFileSync}=require('node:child_process');const assert=require('node:assert/strict');
const source=execFileSync('git',['show','6e493f1:web/src/pages/EvidencePage.tsx'],{encoding:'utf8'});
const handler=source.match(/onClick=\{\(\) => \{ (setEditing\(c.conflictId\); setNote\(c.resolution\); setEditVersion\(c.expectedVersion\)) \}\}/)[1];
let note='unsaved after 412',editing='C-01',version='old';
new Function('c','setEditing','setNote','setEditVersion',handler)({conflictId:'C-01',resolution:'server',expectedVersion:'new'},v=>editing=v,v=>note=v,v=>version=v);
assert.equal(note,'server');assert.equal(version,'new');
const success=source.match(/setSaveError\(''\); setEditing\(null\); onChanged\(\); return r/)[0];
new Function('setSaveError','setEditing','onChanged','r',success)(()=>{},v=>editing=v,()=>{},{});
assert.equal(editing,null);
console.log('Parent defects reproduced: draft/version overwritten; any patch success closes editor. 3 assertions; no browser.');

const assert=require('node:assert/strict');
let networkCalls=0;
globalThis.fetch=()=>{networkCalls++;throw Error('network forbidden')};
for(const name of ['node:http','node:https']){const mod=require(name);mod.request=mod.get=()=>{networkCalls++;throw Error('network forbidden')}}
const {publicSource,textHandoff}=require('/tmp/PUBLICREPORTTEXT-sourceurl-model.cjs');
const m={title:'SYNTHETIC',source:'SYNTHETIC declaration',extractedBy:'SYNTHETIC actor',extractedUtc:'2026-01-01T00:00:00Z',category:'Document',confidentiality:'Restricted',note:''};
const r={caseId:'SYNTHETIC',evidenceId:'EV-301',requestDigest:'a'.repeat(64),sourceSha256:'b'.repeat(64),fileName:'SYNTHETIC.pdf',byteLength:42,metadata:m,registeredUtc:'2026-11-14T00:00:00Z',registeredBy:'SYNTHETIC actor',registeredRole:'Investigator',replayed:false,evidence:{...m,caseId:'SYNTHETIC',evidenceId:'EV-301',sha256:'b'.repeat(64),status:'Verified',accessCount:0}};
const samples=[
'https://127.0.0.1/report.pdf',
'https://192.168.1.1/report.pdf',
'https://example.org/report?token=SYNTHETIC',
'https://localhost/report.pdf',
'https://[::1]/report.pdf',
'https://2130706433/report.pdf',
'https://0x7f000001/report.pdf',
'https://example.org/report#access_token=SYNTHETIC',
];
for(const source of samples){
 assert.equal(publicSource(source),source);
 const handoff=textHandoff(r,source,true);
 assert.equal(handoff.publicMaterial.sourceUrl,source);
 assert.equal(handoff.publicMaterial.verified,false);
 console.log(JSON.stringify({input:source,normalizedHost:new URL(source).hostname,accepted:true,exportedUnchanged:true,verified:handoff.publicMaterial.verified}));
}
assert.equal(networkCalls,0);
console.log(JSON.stringify({cases:samples.length,passed:samples.length,networkCalls,realSecretsUsed:false}));

import assert from 'node:assert/strict';
import {comparePair,compareDeclarations,declarationSnapshot} from './compare.mjs';
// Handwritten JSON-like fixtures only. No API, app, file, clock or model access.
globalThis.fetch=()=>{throw Error('fetch forbidden')};
const hash='a'.repeat(64);
function pair(role){
 const data={caseId:'SYNTH',recordId:'RECORD-A',record:{evidenceId:'EV-1',sourceSha256:hash}};
 return {interview:{state:'available',data},media:{state:'available',data:{caseId:'SYNTH',runId:'RUN-'+role,revision:0,initial:{candidate:{source:{pdf_sha256:hash,image_sha256:hash}},sourceVersions:{pdf:{evidenceId:'EV-1',sha256:hash},image:{evidenceId:'EV-1',sha256:hash}}}}},selection:{caseId:'SYNTH',runId:'RUN-'+role,reviewRevision:0,mediaKind:'image',sourceRole:role},roleDeclaration:{role,basisText:'synthetic',declaredAt:'synthetic',declarerProvenance:'synthetic',boundSnapshot:declarationSnapshot(data)},historyEvents:[]};
}
const bind=p=>{p.roleDeclaration.boundSnapshot=declarationSnapshot(p.interview.data);return p};
const group=pairs=>compareDeclarations({requiredRoles:['pdf','image'],pairs});
const codes=r=>r.issues.map(i=>i.code);
let groups=0;
{
 const a=pair('pdf'),b=pair('image');b.interview.data.recordId='RECORD-B';bind(b);
 assert.equal(comparePair(a).status,'declarations_equal');assert.equal(comparePair(b).status,'declarations_equal');
 const r=group([a,b]);assert.equal(r.status,'indeterminate');assert.ok(codes(r).includes('interview_record_mismatch'));assert.ok(codes(r).includes('interview_snapshot_mismatch'));assert.equal(r.results.length,2);groups++;
}
{
 for(const path of ['evidence','hash','version']){
  const a=pair('pdf'),b=pair('image');
  if(path==='evidence'){b.interview.data.record.evidenceId='EV-2';b.media.data.initial.sourceVersions.image.evidenceId='EV-2'}
  if(path==='hash'){const h='b'.repeat(64);b.interview.data.record.sourceSha256=h;b.media.data.initial.sourceVersions.image.sha256=h;b.media.data.initial.candidate.source.image_sha256=h}
  if(path==='version')b.interview.data.version='synthetic-v2';
  bind(b);assert.equal(comparePair(b).status,'declarations_equal');assert.ok(codes(group([a,b])).includes('interview_snapshot_mismatch'));
 }groups++;
}
{
 const a=pair('pdf'),b=pair('image');b.interview.data.version=null;bind(b);assert.equal(group([a,b]).status,'indeterminate');
 a.interview.data.version=null;bind(a);assert.equal(group([a,b]).status,'declarations_equal');
 delete a.interview.data.record.sourceSha256;b.interview.data.record.sourceSha256=null;bind(a);bind(b);
 const r=group([a,b]);assert.ok(codes(r).includes('interview_snapshot_mismatch'));assert.ok(r.results[0].fields.some(f=>f.status==='missing'));assert.ok(r.results[1].fields.some(f=>f.status==='unknown_null'));groups++;
}
{
 const a=pair('pdf'),b=pair('image');b.interview.data={record:{sourceSha256:hash,evidenceId:'EV-1'},recordId:'RECORD-A',caseId:'SYNTH'};bind(b);
 b.roleDeclaration.boundSnapshot=Object.fromEntries(Object.entries(b.roleDeclaration.boundSnapshot).reverse());
 assert.equal(group([a,b]).status,'declarations_equal');assert.equal(group([b,a]).status,'declarations_equal');groups++;
}
{
 const a=pair('pdf'),b=pair('image');b.interview.state='unavailable';Object.defineProperty(b.interview,'data',{get(){throw Error('unavailable payload traversed')}});
 const r=group([a,b]);assert.equal(r.status,'indeterminate');assert.equal(r.results[1].fields.length,0);groups++;
}
{
 const a=pair('pdf'),b=pair('image'),s=declarationSnapshot(b.interview.data);
 b.historyEvents=[{type:'snapshot_observed',snapshot:{...s,recordId:'RECORD-B'}},{type:'snapshot_observed',snapshot:s}];
 const r=group([a,b]);assert.equal(r.status,'indeterminate');assert.ok(r.results[1].issues.some(i=>i.code==='role_declaration_stale'));groups++;
}
{
 const a=pair('pdf'),b=pair('image');b.interview.data.caseId='OTHER';b.media.data.caseId='OTHER';b.selection.caseId='OTHER';bind(b);
 assert.ok(codes(group([a,b])).includes('case_mismatch'));assert.ok(codes(group([a,b])).includes('interview_snapshot_mismatch'));groups++;
}
console.log(`PASS ${groups} aggregate synthetic groups; no service or trusted history assurance`);

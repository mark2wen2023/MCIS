// Pure comparison of caller-supplied JSON declarations. No imports or ambient services.
export const ROLES = Object.freeze(['audio','pdf','image','image_raw_output','image_candidate']);
const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const own = (v,k) => object(v) && Object.hasOwn(v,k);
const get = (v,path) => path.split('.').reduce((x,k)=>own(x,k)?x[k]:undefined,v);
const copy = v => Array.isArray(v)?v.map(copy):object(v)?Object.fromEntries(Object.keys(v).map(k=>[k,copy(v[k])])):v;
const equal = (a,b) => Object.is(a,b) || (Array.isArray(a)&&Array.isArray(b)&&a.length===b.length&&a.every((v,i)=>equal(v,b[i]))) || (object(a)&&object(b)&&Object.keys(a).length===Object.keys(b).length&&Object.keys(a).every(k=>own(b,k)&&equal(a[k],b[k])));
const text = v => typeof v==='string' && v.trim()===v && v.length>0;
const valid = {
 id:text, evidence:v=>typeof v==='string'&&/^EV-[0-9]+$/.test(v),
 digest:v=>typeof v==='string'&&/^[a-fA-F0-9]{64}$/.test(v),
 revision:v=>Number.isInteger(v)&&v>=0&&v<=1000,
 role:v=>ROLES.includes(v), kind:v=>v==='audio'||v==='image',
 text,
};
function field(fields,path,raw,type){
 const status=raw===undefined?'missing':raw===null?'unknown_null':raw===''?'empty':valid[type](raw)?'present':'invalid';
 const result={path,status,...(raw===undefined?{}:{raw:copy(raw)})};fields.push(result);return result;
}
const ok=f=>f.status==='present';
const roles={
 audio:['initial.machineDraft.source.evidenceId',['initial.machineDraft.source.currentSha256']],
 pdf:['initial.sourceVersions.pdf.evidenceId',['initial.candidate.source.pdf_sha256','initial.sourceVersions.pdf.sha256']],
 image:['initial.sourceVersions.image.evidenceId',['initial.candidate.source.image_sha256','initial.sourceVersions.image.sha256']],
 image_raw_output:['initial.sourceVersions.raw.evidenceId',['initial.sourceVersions.raw.sha256','initial.candidate.source.raw_sha256']],
 image_candidate:['initial.sourceVersions.candidate.evidenceId',['initial.sourceVersions.candidate.sha256']],
};
// Snapshot presence is significant. No substitute transcript/statement version is invented.
function snapshot(d){return Object.fromEntries(['caseId','recordId','record.evidenceId','record.sourceSha256','version'].filter(p=>get(d,p)!==undefined).map(p=>[p,copy(get(d,p))]));}
export function declarationSnapshot(interview){return snapshot(interview);}
// Explicit caller history only: any changed snapshot invalidates permanently, even A→B→A.
export function observeDeclaration(binding,events){
 if(!object(binding)||!Array.isArray(events))return {status:'history_unknown'};
 let stale=false;
 for(const event of events){
  if(!object(event)||event.type!=='snapshot_observed'||!object(event.snapshot))return {status:'history_unknown'};
  if(!equal(binding,event.snapshot))stale=true;
 }
 return {status:stale?'role_declaration_stale':'no_change_reported'};
}
export function comparePair(input){
 const fields=[],issues=[];
 const result={status:'indeterminate',association:'not_established',verification:'not_performed',fields,issues};
 const problem=(code,path)=>issues.push({code,path});
 // Unavailable payloads are intentionally never traversed or echoed.
 for(const side of ['interview','media']){
  const state=input?.[side]?.state;
  if(state!=='available')problem(state==='unread'?'unread':state==='unavailable'?'unavailable':'read_state_invalid',side);
 }
 if(issues.length)return result;
 const i=input.interview.data,m=input.media.data,s=input.selection,d=input.roleDeclaration;
 const f=(label,value,type)=>field(fields,label,value,type);
 const ic=f('interview.caseId',get(i,'caseId'),'id'), ir=f('interview.recordId',get(i,'recordId'),'id');
 const ie=f('interview.record.evidenceId',get(i,'record.evidenceId'),'evidence'),ih=f('interview.record.sourceSha256',get(i,'record.sourceSha256'),'digest');
 const mc=f('media.caseId',get(m,'caseId'),'id'),mr=f('media.runId',get(m,'runId'),'id'),mv=f('media.revision',get(m,'revision'),'revision');
 const sc=f('selection.caseId',get(s,'caseId'),'id'),sr=f('selection.runId',get(s,'runId'),'id'),sv=f('selection.reviewRevision',get(s,'reviewRevision'),'revision');
 const sk=f('selection.mediaKind',get(s,'mediaKind'),'kind'),role=f('selection.sourceRole',get(s,'sourceRole'),'role');
 result.selected=copy(s);
 const diff=(a,b,code)=>{if(ok(a)&&ok(b)&&a.raw!==b.raw)problem(code,a.path+' <> '+b.path)};
 diff(ic,mc,'case_mismatch');diff(sc,mc,'selection_mismatch');diff(sr,mr,'selection_mismatch');diff(sv,mv,'selection_mismatch');
 if(ok(role)&&ok(sk)&&((role.raw==='audio')!==(sk.raw==='audio')))problem('role_mismatch','selection');
 const dr=f('roleDeclaration.role',get(d,'role'),'role');
 f('roleDeclaration.basisText',get(d,'basisText'),'text');
 // Timestamp/provenance are opaque caller declarations, not clock or identity verification.
 f('roleDeclaration.declaredAt',get(d,'declaredAt'),'text');f('roleDeclaration.declarerProvenance',get(d,'declarerProvenance'),'text');
 if(!ok(dr))problem('role_unknown','roleDeclaration.role');else diff(dr,role,'role_mismatch');
 const binding=get(d,'boundSnapshot');
 if(!object(binding))problem('role_unknown','roleDeclaration.boundSnapshot');
 else {
  if(!equal(binding,snapshot(i)))problem('role_declaration_stale','roleDeclaration.boundSnapshot');
  const history=observeDeclaration(binding,input.historyEvents);
  if(history.status!=='no_change_reported')problem(history.status,'historyEvents');
 }
 // No source payload comparison across cases or ambiguous role/kind contexts.
 if(ok(ic)&&ok(mc)&&ic.raw===mc.raw&&ok(role)&&ok(sk)&&((role.raw==='audio')===(sk.raw==='audio'))){
  const [idPath,hashPaths]=roles[role.raw];
  const me=f('media.'+idPath,get(m,idPath),'evidence');
  const hashes=hashPaths.map(p=>f('media.'+p,get(m,p),'digest'));
  diff(ie,me,'id_mismatch');
  if(hashes.length===2&&hashes.every(ok)&&hashes[0].raw.toLowerCase()!==hashes[1].raw.toLowerCase())problem('source_inconsistent',hashPaths.join(' <> '));
  // Each digest mismatch is independent of ID mismatch and the other digest's validity.
  for(const hash of hashes)if(ok(ih)&&ok(hash)&&ih.raw.toLowerCase()!==hash.raw.toLowerCase())problem('digest_mismatch',hash.path);
 }
 for(const item of fields)if(!ok(item))problem('field_'+item.status,item.path);
 if(!issues.length)result.status='declarations_equal';
 else if(issues.some(x=>['case_mismatch','role_mismatch','id_mismatch','digest_mismatch','source_inconsistent','selection_mismatch'].includes(x.code)))result.status='not_equal_or_incomplete';
 // ir is independently validated; media runId is never compared to interview recordId.
 return result;
}
// Pairs are explicitly supplied by caller; never paired by position/hash/file name.
export function compareDeclarations(input){
 const results=Array.isArray(input?.pairs)?input.pairs.map(comparePair):[];
 const issues=[];const required=input?.requiredRoles;
 if(!Array.isArray(required)||!required.length||required.some(r=>!ROLES.includes(r))||new Set(required).size!==required.length)issues.push({code:'required_roles_invalid'});
 if(!Array.isArray(input?.pairs)||!input.pairs.length)issues.push({code:'selection_missing'});
 const counts=new Map();
 const cases=new Set(results.flatMap(r=>r.fields.filter(f=>f.path==='interview.caseId'&&ok(f)).map(f=>f.raw)));
 if(cases.size>1)issues.push({code:'case_mismatch'});
 for(const pair of Array.isArray(input?.pairs)?input.pairs:[]){const role=pair?.selection?.sourceRole;counts.set(role,(counts.get(role)??0)+1)}
 for(const [role,count]of counts)if(count>1)issues.push({code:'duplicate_role',role});
 if(Array.isArray(required))for(const role of required)if(!counts.has(role))issues.push({code:'required_role_missing',role});
 if(Array.isArray(required))for(const role of counts.keys())if(!required.includes(role))issues.push({code:'unexpected_role',role});
 return {status:!issues.length&&results.length&&results.every(r=>r.status==='declarations_equal')?'declarations_equal':'indeterminate',association:'not_established',verification:'not_performed',results,issues};
}

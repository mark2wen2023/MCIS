/** Display projection only. This does not establish identity or grant authority. */
type Obj=Record<string,unknown>
const fail=():never=>{throw Error('已保存结果与当前案件、请求或来源版本不一致。')}
const obj=(v:unknown):Obj=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Obj:fail()
const text=(v:unknown,max=512):string=>typeof v==='string'&&v.length>0&&v.length<=max&&!/[\u0000-\u001f]/.test(v)?v:fail()
const uuid=(v:unknown)=>{const s=text(v,36);return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(s)?s:fail()}
const array=(v:unknown,max=4096):unknown[]=>Array.isArray(v)&&v.length<=max?v:fail()
const keys=(v:Obj,names:string[])=>{if(Object.keys(v).some(k=>!names.includes(k))||names.some(k=>!(k in v)))fail()}
function canonical(v:unknown,depth=0,budget={nodes:0,units:0}):string{
  if(depth>32||++budget.nodes>100000)fail()
  if(typeof v==='string'){budget.units+=v.length;if(budget.units>2*1024*1024)fail()}
  if(v===null||typeof v==='boolean')return JSON.stringify(v)
  if(typeof v==='number')return Number.isFinite(v)?JSON.stringify(v):fail()
  if(typeof v==='string')return JSON.stringify(v)
  if(Array.isArray(v))return '['+v.map(x=>canonical(x,depth+1,budget)).join(',')+']'
  const o=obj(v);const names=Object.keys(o);budget.units+=names.reduce((n,k)=>n+k.length,0);if(budget.units>2*1024*1024||names.length>100000)fail();return '{'+names.sort().map(k=>JSON.stringify(k)+':'+canonical(o[k],depth+1,budget)).join(',')+'}'
}
export type ExpectedStoredScope={caseId:string;runId:string;request:unknown;generationSnapshot:unknown}
export type StoredUnreviewedResult={caseId:string;runId:string;createdUtc:string;status:'unreviewed';sourceIds:string[];conflicts:{id:string;summary:string}[];importDiagnosticCount:number;conflictDiagnosticCount:number;uncalibratedSources:string[];coreImplementation:'not_attested'}
export function storedResult(raw:unknown,expected:ExpectedStoredScope):StoredUnreviewedResult{
  // A JSON-compatible bounded value from a future authenticated adapter, not an
  // uploaded worksheet. Never use this parser as server authorization.
  if(canonical(raw).length>2*1024*1024)fail()
  const v=obj(raw);keys(v,['runId','caseId','status','observationApproval','usableAsWriteCredential','createdUtc','request','generationSnapshot','serverPreview','processing'])
  if(text(v.caseId,64)!==text(expected.caseId,64)||uuid(v.runId)!==uuid(expected.runId)||v.status!=='unreviewed'||v.observationApproval!=='not_assessed'||v.usableAsWriteCredential!==false)fail()
  const created=text(v.createdUtc,64);if(!Number.isFinite(Date.parse(created)))fail()
  if(canonical(v.request)!==canonical(expected.request)||canonical(v.generationSnapshot)!==canonical(expected.generationSnapshot))fail()
  const request=obj(v.request),snap=obj(v.generationSnapshot)
  const ids=array(request.sources,4).map(x=>text(obj(x).evidenceId,64));if(!ids.length||new Set(ids).size!==ids.length)fail()
  if(snap.caseId!==v.caseId)fail();uuid(snap.caseIncarnation)
  const epoch=text(snap.caseEpochUtc,64);if(!Number.isFinite(Date.parse(epoch)))fail()
  const sources=array(snap.sourceSnapshots,4);if(sources.length!==ids.length)fail()
  keys(snap,['caseId','caseIncarnation','caseEpochUtc','sourceIdentities','sourceSnapshots','reportSnapshots'])
  const hash=(v:unknown)=>{const h=text(v,64);return /^[a-f0-9]{64}$/.test(h)?h:fail()}
  const snapshot=(x:unknown)=>{const s=obj(x);hash(s.sourceSha256);hash(s.registrationDigest);if(!Number.isSafeInteger(s.byteLength)||Number(s.byteLength)<0||Number(s.byteLength)>8388608||!Number.isFinite(Date.parse(text(s.registeredUtc,64))))fail();return s}
  sources.forEach((x,i)=>{const s=snapshot(x);if(s.evidenceId!==ids[i])fail()})
  const parents=array(request.sources,4).map(obj).filter(s=>s.parentReport!=null)
  const reports=array(snap.reportSnapshots,4);if(reports.length!==parents.length)fail()
  reports.forEach((x,i)=>{const p=snapshot(x),decl=obj(parents[i].parentReport);if(p.extractEvidenceId!==parents[i].evidenceId||p.evidenceId!==decl.evidenceId||p.sourceSha256!==decl.sourceSha256||p.relationshipStatus!=='user_declared_not_verified'||obj(parents[i].comparisonContext).sourceNature!=='report_extract')fail()})
  const all=[...sources,...reports].map(obj),sourceIds=[...new Set(all.map(s=>text(s.evidenceId,64)))].sort()
  const identities=array(snap.sourceIdentities,8).map(obj)
  if(identities.length!==sourceIds.length)fail()
  identities.forEach((i,n)=>{if(i.evidenceId!==sourceIds[n]||i.caseId!==v.caseId||i.caseIncarnation!==snap.caseIncarnation||i.version!==1||!Number.isSafeInteger(i.registeredSeq)||Number(i.registeredSeq)<1)fail();uuid(i.incarnation);const matching=all.filter(s=>s.evidenceId===i.evidenceId);if(matching.some(s=>s.sourceSha256!==hash(i.sourceSha256)||s.registrationDigest!==hash(i.requestDigest)||s.registeredUtc!==i.registeredUtc))fail()})
  const p=obj(v.processing);keys(p,['serviceProtocolVersion','alignmentAdapterVersion','coreProtocolVersion','coreImplementationVersionStatus'])
  if(p.serviceProtocolVersion!=='mcis-internal-unreviewed-save-v1'||p.alignmentAdapterVersion!=='registered-csv-preflight-v1'||p.coreProtocolVersion!=='mcis-core-align-json-v1'||p.coreImplementationVersionStatus!=='not_attested')fail()
  const preview=obj(v.serverPreview);if(preview.caseId!==v.caseId||preview.caseEpochUtc!==epoch)fail()
  const result=obj(preview.result);if(result.caseId!==v.caseId)fail()
  const conflicts=array(result.conflicts).map(x=>{const c=obj(x);if(c.caseId!==v.caseId||!ids.includes(text(obj(c.a).sourceLabel,64))||!ids.includes(text(obj(c.b).sourceLabel,64)))fail();return {id:text(c.conflictId,128),summary:text(c.summary,4096)}})
  if(new Set(conflicts.map(c=>c.id)).size!==conflicts.length)fail()
  const cal=obj(result.calibration);if(typeof cal.allCalibrated!=='boolean')fail()
  const uncal=array(cal.uncalibratedSources,4).map(x=>text(x,64));if(uncal.some(id=>!ids.includes(id)))fail()
  const diagnostics=(value:unknown)=>array(value).map(x=>{const d=obj(x);if(d.sourceId!==null&&!ids.includes(text(d.sourceId,64)))fail();text(d.severity,32);return d}).length
  return {caseId:expected.caseId,runId:expected.runId,createdUtc:created,status:'unreviewed',sourceIds:[...ids],conflicts,importDiagnosticCount:diagnostics(result.importDiagnostics),conflictDiagnosticCount:diagnostics(result.conflictDiagnostics),uncalibratedSources:uncal,coreImplementation:'not_attested'}
}

import type { AlignPreview, PreviewKind } from './types'
export type ComparisonContext={vesselLabel:string;sourceNature:'report_extract'|'sensor_export'|'other'|'unknown';sourceTitle:string;citation:string;timeBasis:string;headingReference:'true'|'magnetic'|'unknown'|null}
export const blankContext=():ComparisonContext=>({vesselLabel:'',sourceNature:'unknown',sourceTitle:'',citation:'',timeBasis:'',headingReference:null})
export type ParentReport={evidenceId:string;sourceSha256:string}
export type RegisteredSelection={evidenceId:string;timeColumn:string;column:string;kind:PreviewKind;comparisonContext?:ComparisonContext;parentReport?:ParentReport}
export type Snapshot={evidenceId:string;sourceSha256:string;registrationDigest:string;byteLength:number;registeredUtc:string}
export type ReportSnapshot=Snapshot&{extractEvidenceId:string;relationshipStatus:'user_declared_not_verified'}
export type RegisteredResult=AlignPreview&{sourceSnapshots:Snapshot[];reportSnapshots?:ReportSnapshot[];sourceBinding:'transient-local-intake-bytes';observationApproval:'not_assessed';comparisonScope?:{status:'unscoped'|'user_declared_not_verified';sources:{evidenceId:string;context:ComparisonContext}[]}}
export const blankRegistered=():RegisteredSelection=>({evidenceId:'',timeColumn:'',column:'',kind:'Heading'})
export function registeredBody(rows:RegisteredSelection[]){
  if(!rows.length||rows.length>4||new Set(rows.map(r=>r.evidenceId)).size!==rows.length)throw Error('请选择1–4份不同证据。')
  const scoped=rows.some(r=>r.comparisonContext!==undefined)
  const normalized=rows.map(r=>r.comparisonContext?normalizeContext(r.comparisonContext,r.kind):undefined)
  if(scoped&&(normalized.some(c=>!c)||new Set(normalized.map(c=>c?.vesselLabel)).size!==1||new Set(rows.map(r=>r.kind)).size!==1))throw Error('本次来源须声明同一船舶、同一物理量；不得混合有无声明的来源。')
  return {sources:rows.map((r,i)=>{
    if(!/^EV-[0-9]{3,}$/.test(r.evidenceId)||!r.timeColumn.trim()||!r.column.trim()||r.timeColumn===r.column||r.timeColumn.length>128||r.column.length>128||!['Heading','CourseOverGround','SpeedOverGround'].includes(r.kind))throw Error('请选择证据并填写不同的时间列、数值列及类型。')
    const parent=r.parentReport
    if(parent&&(normalized[i]?.sourceNature!=='report_extract'||typeof parent.evidenceId!=='string'||!/^EV-[0-9]{3,}$/.test(parent.evidenceId)||parent.evidenceId.length>32||parent.evidenceId===r.evidenceId||typeof parent.sourceSha256!=='string'||!/^[a-f0-9]{64}$/.test(parent.sourceSha256)))throw Error('父报告须为另一个本案登记文件及其当前SHA-256，并明确声明为报告摘录。')
    return {evidenceId:r.evidenceId,...(scoped?{comparisonContext:normalized[i]}:{}),...(parent?{parentReport:{evidenceId:parent.evidenceId,sourceSha256:parent.sourceSha256}}:{}),csvMapping:{timeColumn:r.timeColumn,columns:[{column:r.column,kind:r.kind}]}}
  })}
}
export function registeredResult(value:unknown,caseId:string,ids:string[],expected?:RegisteredSelection[],expectedSources?:{evidenceId:string;sourceSha256:string}[]):RegisteredResult{
  const v=value as RegisteredResult
  if(!v||v.caseId!==caseId||v.previewOnly!==true||v.persisted!==false||v.sourceBinding!=='transient-local-intake-bytes'||v.observationApproval!=='not_assessed'||typeof v.caseEpochUtc!=='string'||!v.result||v.result.caseId!==caseId)throw Error('返回范围或来源声明不匹配，结果未采用。')
  if(!Array.isArray(v.sourceSnapshots)||v.sourceSnapshots.length!==ids.length||v.sourceSnapshots.some((s,i)=>!s||s.evidenceId!==ids[i]||typeof s.sourceSha256!=='string'||typeof s.registrationDigest!=='string'||!/^[a-f0-9]{64}$/.test(s.sourceSha256)||!/^[a-f0-9]{64}$/.test(s.registrationDigest)||!Number.isInteger(s.byteLength)||s.byteLength<0||s.byteLength>262144||typeof s.registeredUtc!=='string'))throw Error('来源快照与本次选择不一致。')
  if(expectedSources&&(expectedSources.length!==ids.length||expectedSources.some((s,i)=>s.evidenceId!==ids[i]||s.sourceSha256!==v.sourceSnapshots[i].sourceSha256)))throw Error('登记来源版本已变化，请刷新证据清单并重新核查。')
  const r=v.result
  if(!Array.isArray(r.conflicts)||r.conflicts.some(c=>typeof c?.conflictId!=='string'||typeof c.summary!=='string'||(c.delta!=null&&typeof c.delta!=='number'))||!Array.isArray(r.clockOffsets)||!r.calibration||!Array.isArray(r.calibration.uncalibratedSources)||r.calibration.uncalibratedSources.some(x=>typeof x!=='string')||!Array.isArray(r.calibration.sources)||!Array.isArray(r.importDiagnostics)||!Array.isArray(r.conflictDiagnostics)||!r.stats)throw Error('预览结构无法核对。')
  const numberOrNull=(n:unknown)=>n==null||(typeof n==='number'&&Number.isFinite(n))
  if(!Number.isFinite(Date.parse(v.caseEpochUtc))||typeof r.calibration.allCalibrated!=='boolean'||(r.calibration.error!=null&&typeof r.calibration.error!=='string')||r.conflicts.length>4096||r.clockOffsets.some(o=>!o||typeof o.sourceId!=='string'||typeof o.status!=='string'||!numberOrNull(o.offsetSeconds)||!numberOrNull(o.uncertaintySeconds))||r.conflicts.some(c=>!numberOrNull(c.delta)||(c.deltaUnit!=null&&typeof c.deltaUnit!=='string'))||typeof r.stats!=='object'||Array.isArray(r.stats)||Object.values(r.stats).some(n=>typeof n!=='number'||!Number.isFinite(n)))throw Error('预览字段无法核对。')
  if(r.conflicts.some(c=>(c as typeof c & {caseId?:string}).caseId!==caseId||!c.a||!c.b||!ids.includes(c.a.sourceLabel)||!ids.includes(c.b.sourceLabel))||r.clockOffsets.some(o=>!ids.includes(o.sourceId))||r.calibration.uncalibratedSources.some(id=>!ids.includes(id)))throw Error('结果包含本次范围之外的案件或来源。')
  if(expected){
    const sent=registeredBody(expected).sources
    if(v.comparisonScope?.status!=='user_declared_not_verified'||!Array.isArray(v.comparisonScope.sources)||v.comparisonScope.sources.length!==sent.length||v.comparisonScope.sources.some((s,i)=>s.evidenceId!==sent[i].evidenceId||!sameContext(s.context,sent[i].comparisonContext)))throw Error('人工声明回显不一致，结果未采用。')
  }
  const parents=(expected??[]).filter(s=>s.parentReport)
  const reports=v.reportSnapshots===undefined&&parents.length===0?[]:v.reportSnapshots
  if(!Array.isArray(reports)||reports.length!==parents.length||reports.some((s,i)=>!s||s.extractEvidenceId!==parents[i].evidenceId||s.evidenceId!==parents[i].parentReport!.evidenceId||s.sourceSha256!==parents[i].parentReport!.sourceSha256||s.relationshipStatus!=='user_declared_not_verified'||typeof s.registrationDigest!=='string'||!/^[a-f0-9]{64}$/.test(s.registrationDigest)||!Number.isInteger(s.byteLength)||s.byteLength<0||s.byteLength>8388608||typeof s.registeredUtc!=='string'||!Number.isFinite(Date.parse(s.registeredUtc))))throw Error('父报告版本或关联声明无法核对，结果未采用。')
  return v
}

function normalizeContext(c:ComparisonContext,kind:PreviewKind):ComparisonContext{
  const text=(v:string,n:number)=>{if(typeof v!=='string'||!v.trim()||v.length>n||/[\u0000-\u001f]/.test(v))throw Error('请填写单行、限长的船舶、来源名称、页/图表/记录定位和时间口径。');return v.trim()}
  if(!['report_extract','sensor_export','other','unknown'].includes(c.sourceNature))throw Error('请选择来源性质。')
  if(kind==='Heading'?c.headingReference!=='true':c.headingReference!==null)throw Error('船首向须明确声明为真航向；磁航向或未知基准暂不比较，不自动换算。')
  return {vesselLabel:text(c.vesselLabel,128),sourceNature:c.sourceNature,sourceTitle:text(c.sourceTitle,200),citation:text(c.citation,500),timeBasis:text(c.timeBasis,300),headingReference:c.headingReference}
}
function sameContext(a:ComparisonContext,b:ComparisonContext|undefined){return !!a&&!!b&&['vesselLabel','sourceNature','sourceTitle','citation','timeBasis','headingReference'].every(k=>a[k as keyof ComparisonContext]===b[k as keyof ComparisonContext])}

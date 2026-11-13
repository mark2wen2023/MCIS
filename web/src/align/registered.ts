import type { AlignPreview, PreviewKind } from './types'
export type RegisteredSelection={evidenceId:string;timeColumn:string;column:string;kind:PreviewKind}
export type Snapshot={evidenceId:string;sourceSha256:string;registrationDigest:string;byteLength:number;registeredUtc:string}
export type RegisteredResult=AlignPreview&{sourceSnapshots:Snapshot[];sourceBinding:'transient-local-intake-bytes';observationApproval:'not_assessed'}
export const blankRegistered=():RegisteredSelection=>({evidenceId:'',timeColumn:'',column:'',kind:'Heading'})
export function registeredBody(rows:RegisteredSelection[]){
  if(!rows.length||rows.length>4||new Set(rows.map(r=>r.evidenceId)).size!==rows.length)throw Error('请选择1–4份不同证据。')
  return {sources:rows.map(r=>{
    if(!/^EV-[0-9]{3,}$/.test(r.evidenceId)||!r.timeColumn.trim()||!r.column.trim()||r.timeColumn===r.column||r.timeColumn.length>128||r.column.length>128||!['Heading','CourseOverGround','SpeedOverGround'].includes(r.kind))throw Error('请选择证据并填写不同的时间列、数值列及类型。')
    return {evidenceId:r.evidenceId,csvMapping:{timeColumn:r.timeColumn,columns:[{column:r.column,kind:r.kind}]}}
  })}
}
export function registeredResult(value:unknown,caseId:string,ids:string[]):RegisteredResult{
  const v=value as RegisteredResult
  if(!v||v.caseId!==caseId||v.previewOnly!==true||v.persisted!==false||v.sourceBinding!=='transient-local-intake-bytes'||v.observationApproval!=='not_assessed'||typeof v.caseEpochUtc!=='string'||!v.result||v.result.caseId!==caseId)throw Error('返回范围或来源声明不匹配，结果未采用。')
  if(!Array.isArray(v.sourceSnapshots)||v.sourceSnapshots.length!==ids.length||v.sourceSnapshots.some((s,i)=>!s||s.evidenceId!==ids[i]||typeof s.sourceSha256!=='string'||typeof s.registrationDigest!=='string'||!/^[a-f0-9]{64}$/.test(s.sourceSha256)||!/^[a-f0-9]{64}$/.test(s.registrationDigest)||!Number.isInteger(s.byteLength)||s.byteLength<0||s.byteLength>262144||typeof s.registeredUtc!=='string'))throw Error('来源快照与本次选择不一致。')
  const r=v.result
  if(!Array.isArray(r.conflicts)||r.conflicts.some(c=>typeof c?.conflictId!=='string'||typeof c.summary!=='string'||(c.delta!=null&&typeof c.delta!=='number'))||!Array.isArray(r.clockOffsets)||!r.calibration||!Array.isArray(r.calibration.uncalibratedSources)||r.calibration.uncalibratedSources.some(x=>typeof x!=='string')||!Array.isArray(r.calibration.sources)||!Array.isArray(r.importDiagnostics)||!Array.isArray(r.conflictDiagnostics)||!r.stats)throw Error('预览结构无法核对。')
  const numberOrNull=(n:unknown)=>n==null||(typeof n==='number'&&Number.isFinite(n))
  if(!Number.isFinite(Date.parse(v.caseEpochUtc))||typeof r.calibration.allCalibrated!=='boolean'||(r.calibration.error!=null&&typeof r.calibration.error!=='string')||r.conflicts.length>4096||r.clockOffsets.some(o=>!o||typeof o.sourceId!=='string'||typeof o.status!=='string'||!numberOrNull(o.offsetSeconds)||!numberOrNull(o.uncertaintySeconds))||r.conflicts.some(c=>!numberOrNull(c.delta)||(c.deltaUnit!=null&&typeof c.deltaUnit!=='string'))||typeof r.stats!=='object'||Array.isArray(r.stats)||Object.values(r.stats).some(n=>typeof n!=='number'||!Number.isFinite(n)))throw Error('预览字段无法核对。')
  if(r.conflicts.some(c=>(c as typeof c & {caseId?:string}).caseId!==caseId||!c.a||!c.b||!ids.includes(c.a.sourceLabel)||!ids.includes(c.b.sourceLabel))||r.clockOffsets.some(o=>!ids.includes(o.sourceId))||r.calibration.uncalibratedSources.some(id=>!ids.includes(id)))throw Error('结果包含本次范围之外的案件或来源。')
  return v
}

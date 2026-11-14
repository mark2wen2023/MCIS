import {registeredBody,registeredResult,type RegisteredResult,type RegisteredSelection} from './registered'

/** Local, editable working copy. Not a receipt, approval or import format. */
export function reviewWorksheet(value:RegisteredResult,rows:RegisteredSelection[],exportedUtc:string){
  if(!Number.isFinite(Date.parse(exportedUtc)))throw Error('导出时间无效')
  const sources=registeredBody(rows).sources
  const checked=registeredResult(value,value.caseId,rows.map(r=>r.evidenceId),rows)
  const snapshot=(s:RegisteredResult['sourceSnapshots'][number])=>({evidenceId:s.evidenceId,sourceSha256:s.sourceSha256,registrationDigest:s.registrationDigest,byteLength:s.byteLength,registeredUtc:s.registeredUtc})
  return {
    format:'mcis-timeline-unreviewed-worksheet-v1',
    status:'unreviewed_working_copy',
    authority:'none',
    importSupported:false,
    exportedUtc,
    notice:'仅本地导出的可编辑工作副本，未经审核，不是可信凭据，不可导入审批。导出时间不是计算时间；来源版本可能随后变化，正式复核前须重新核查。',
    reviewChecklist:['核对当前原件与所列SHA-256，重新运行核查','核对摘录、船舶、单位、时间口径及父报告关系','区分共同来源与独立印证；核对导入诊断及钟差','保留异议并由调查组复核；本文件不能批准事实或写入时间线'],
    caseId:checked.caseId,caseEpochUtc:checked.caseEpochUtc,
    request:{sources},
    sourceSnapshots:checked.sourceSnapshots.map(snapshot),
    reportSnapshots:(checked.reportSnapshots??[]).map(s=>({...snapshot(s),extractEvidenceId:s.extractEvidenceId,relationshipStatus:s.relationshipStatus})),
    observationApproval:'not_assessed',
    previewOnly:true,persisted:false,
    result:{
      conflicts:checked.result.conflicts.map(c=>({conflictId:c.conflictId,summary:c.summary,delta:c.delta??null,deltaUnit:c.deltaUnit??null})),
      clockOffsets:checked.result.clockOffsets.map(o=>({sourceId:o.sourceId,offsetSeconds:o.offsetSeconds??null,uncertaintySeconds:o.uncertaintySeconds??null,status:o.status})),
      calibration:{allCalibrated:checked.result.calibration.allCalibrated,uncalibratedSources:[...checked.result.calibration.uncalibratedSources]},
      diagnostics:{detailsExported:false,importCount:checked.result.importDiagnostics.length,conflictCount:checked.result.conflictDiagnostics.length,calibrationSourceCount:checked.result.calibration.sources.length,notice:'诊断与校准源全文未导出，请在核查界面逐项检查，数量不代表通过。'},
      stats:Object.fromEntries(['sourcesImported','tracks','linesRead','sentencesUsed','anchorCount','manualAnchorCount'].filter(k=>k in checked.result.stats).map(k=>[k,checked.result.stats[k]])),
    },
  }
}

export function downloadWorksheet(value:RegisteredResult,rows:RegisteredSelection[]){
  const content=JSON.stringify(reviewWorksheet(value,rows,new Date().toISOString()),null,2)
  const url=URL.createObjectURL(new Blob([content],{type:'application/json;charset=utf-8'}))
  try{
    const anchor=document.createElement('a');anchor.href=url;anchor.download='mcis-timeline-unreviewed.json'
    document.body.append(anchor)
    try{anchor.click()}finally{anchor.remove()}
  }finally{setTimeout(()=>URL.revokeObjectURL(url),0)}
}

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { renderToStaticMarkup } from 'react-dom/server'
import { blankSource, mayPreview, previewPayload } from '../src/align/model'
import type { AlignPreview, PreviewSource } from '../src/align/types'
Object.defineProperty(globalThis,'localStorage',{configurable:true,value:{getItem:()=>null}})
let n=0
function check(ok:unknown,label:string){assert.ok(ok,label);n++}
const s:PreviewSource={sourceId:'A',text:'time,cog\n2026-01-01T00:00:00Z,45',csvMapping:{timeColumn:'time',columns:[{column:'cog',kind:'CourseOverGround'}]}}
async function main(){
  const {PreviewResult}=await import('../src/align/AlignPreviewPanel')
  check(blankSource(1).text==='', 'no invented CSV data')
  check(JSON.stringify(previewPayload([s]))===JSON.stringify({sources:[s]}),'explicit payload')
  const evil={...s,path:'/private/file',csvMapping:{...s.csvMapping,path:'/private'}}
  check(!JSON.stringify(previewPayload([evil])).includes('path'),'client reconstructs fields')
  for(const sources of [[],[s,s],Array(5).fill(s),[{...s,sourceId:' '}],[{...s,text:'中'.repeat(87382)}],[{...s,csvMapping:{...s.csvMapping,columns:[]}}]]){
    assert.throws(()=>previewPayload(sources));n++
  }
  check(previewPayload([{...s,text:'中'.repeat(87381)+'a'}]).sources.length===1,'UTF8 exact boundary')
  for(const role of ['ReadWrite','ReadOnly','Redacted','Deny','unknown'])check(mayPreview({User:{timeline:role}},'User')===['ReadWrite','ReadOnly','Redacted'].includes(role),role)
  check(!mayPreview(null,'User'),'unknown policy failclosed')
  const fixture:AlignPreview={previewOnly:true,persisted:false,caseId:'synthetic',caseEpochUtc:'2026-01-01T00:00:00Z',result:{caseId:'synthetic',conflicts:[],clockOffsets:[],calibration:{allCalibrated:false,uncalibratedSources:['A'],sources:[],error:'no anchors'},importDiagnostics:[{code:'synthetic-warning'}],conflictDiagnostics:[],stats:{linesRead:1}}}
  const html=renderToStaticMarkup(<PreviewResult value={fixture}/>)
  for(const text of ['未入库','未改人工复核','未全部校准','no anchors','不能当作0秒','不代表数据完整','synthetic-warning','统计'])check(html.includes(text),text)
  check(!html.includes('<button'),'no persistence action in result')
  const unknown=renderToStaticMarkup(<PreviewResult value={{...fixture,result:{...fixture.result,clockOffsets:[{sourceId:'A',status:'unknown'}]}}}/>)
  check(unknown.includes('未知'),'missing offset not zero')
  const page=readFileSync('src/pages/EvidencePage.tsx','utf8')
  check(page.includes('key={`${caseId}:${requestedId}:${who}`}'),'whole page identity isolation')
  check(page.includes('<details className="w4-preview-disclosure">'),'preview collapsed by default, existing evidence first')
  check(page.includes('<summary>临时CSV预览，未入库</summary>'),'explicit preview disclosure')
  const ui=readFileSync('src/align/AlignPreviewPanel.tsx','utf8')
  check(ui.includes('无offset按UTC解释')&&ui.includes('不自动转换m/s'),'units/time visible')
  check(ui.includes('测量对象及单位一致'),'no automatic two-vessel assumption')
  check(!ui.includes("'/core/align'"),'no unsafe legacy API')
  console.log(`W4.1 ${n} model/static-render checks passed (not browser interaction).`)
}
main().catch(e=>{console.error(e);process.exitCode=1})

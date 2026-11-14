import { strict as assert } from 'node:assert'
import { readFileSync } from 'node:fs'
import { renderToStaticMarkup } from 'react-dom/server'
import { parsePreview,parseReceipt } from '../src/packageIntake/model'
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
async function main(){
const { IntakeSummary,WorkingRecordsSummary }=await import('../src/packageIntake/PackageIntakePanel')
const working={version:'MCIS-WORKING-RECORDS-1' as const,interviewCount:0,reportCount:1,reportSnapshotCount:1,manualReceiptCount:0,receiptMode:'archive-only' as const,identityMode:'unverified-self-reported' as const}
const p={profile:'MCIS-BASIC-INTAKE-1',packageVersion:'1.4.0' as const,caseId:'SYNTHETIC-14',title:'Synthetic',sourceSha256:'a'.repeat(64),byteLength:100,counts:{evidence:0},warnings:[],hfacsExtension:null,workingRecordsExtension:working}
assert.deepEqual(parsePreview(p),p)
for(const patch of [
 {packageVersion:'1.5.0'}, {workingRecordsExtension:null}, {workingRecordsExtension:undefined},
 {workingRecordsExtension:{...working,version:'MCIS-WORKING-RECORDS-2',trackReceiptCount:1}},
 {workingRecordsExtension:{...working,trackReceiptCount:1}}, {workingRecordsExtension:{...working,reportCount:-1}},
 {hfacsExtension:{}}, {hfacsExtension:undefined},
]) assert.throws(()=>parsePreview({...p,...patch}))
const hfacs={version:'MCIS-HFACS-PACKAGE-1',draftCount:0,revisionCount:0,receiptCount:0,receiptMode:'archive-only',identityMode:'unverified-self-reported'}
assert.doesNotThrow(()=>parsePreview({...p,hfacsExtension:hfacs}))
assert.doesNotThrow(()=>parsePreview({...p,packageVersion:'1.2.0'}))
assert.doesNotThrow(()=>parsePreview({...p,packageVersion:'1.3.0',workingRecordsExtension:{...working,version:'MCIS-WORKING-RECORDS-2',trackReceiptCount:1}}))
const receipt={...p,importedUtc:'2026-11-14T00:00:00Z',replayed:false}
assert.equal(parseReceipt(receipt,p).packageVersion,'1.4.0')
for(const patch of [{packageVersion:'1.2.0'},{workingRecordsExtension:{...working,reportCount:2}},{sourceSha256:'b'.repeat(64)}])assert.throws(()=>parseReceipt({...receipt,...patch},p))
const html=renderToStaticMarkup(<IntakeSummary preview={p}/>);
for(const text of ['1.4.0 受限工作记录归档','最多256条','不支持时间线与航迹导入历史混合','安全建议','征求意见','不代表本次审核'])assert.ok(html.includes(text),text)
assert.ok(!html.includes('1.2.0 受限工作记录归档'))
assert.ok(!renderToStaticMarkup(<WorkingRecordsSummary extension={working} packageVersion="1.2.0"/>).includes('时间线恢复范围'))
const { PackagePanel }=await import('../src/packages/PackagePanel')
const exportPanel=renderToStaticMarkup(<PackagePanel who={'LeadInvestigator\nSynthetic'}/>);
assert.ok(exportPanel.includes('1.4.0为工作记录与时间线事件组合'))
if(process.env.MCIS_REAL_TIMELINE_RESPONSES){
 const actual=JSON.parse(readFileSync(process.env.MCIS_REAL_TIMELINE_RESPONSES,'utf8'))
 const preview=parsePreview(actual.preview)
 assert.equal(preview.packageVersion,'1.4.0')
 parseReceipt(actual.commit,preview);parseReceipt(actual.lookup,preview)
 assert.ok(renderToStaticMarkup(<IntakeSummary preview={preview}/>).includes('1.4.0 受限工作记录归档'))
 console.log('Real ASGI API preview/commit/lookup responses passed frontend parsing and SSR (not browser interaction)')
}
console.log('1.4 parser/receipt binding/render scope assertions passed (synthetic inputs; no backend mocks claimed as real workflow)')

}
main().catch(e=>{console.error(e);process.exit(1)})

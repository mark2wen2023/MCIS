import assert from 'node:assert/strict'
import {renderToStaticMarkup} from 'react-dom/server'
import {parsePreview,parseReceipt} from '../src/packageIntake/model'
Object.defineProperty(globalThis,'localStorage',{configurable:true,value:{getItem:()=>null,setItem:()=>{}}})
async function main(){
const {WorkingRecordsSummary}=await import('../src/packageIntake/PackageIntakePanel')
const w={version:'MCIS-WORKING-RECORDS-1',interviewCount:1,reportCount:2,reportSnapshotCount:4,manualReceiptCount:3,receiptMode:'archive-only',identityMode:'unverified-self-reported'}
const p={profile:'MCIS-BASIC-INTAKE-1',caseId:'SYN',title:'Synthetic',sourceSha256:'a'.repeat(64),byteLength:12,packageVersion:'1.2.0',hfacsExtension:null,workingRecordsExtension:w,counts:{evidence:1},warnings:[]}
assert.equal(parsePreview(p).workingRecordsExtension?.reportCount,2)
for(const x of [undefined,null,{}, {...w,manualReceiptCount:2049},{...w,interviewCount:-1},{...w,reportCount:1.2},{...w,receiptMode:'active'},{...w,identityMode:'verified'},{...w,unknown:1}])assert.throws(()=>parsePreview({...p,workingRecordsExtension:x}))
for(const version of ['1.0.0','1.1.0'])assert.throws(()=>parsePreview({...p,packageVersion:version}))
assert.equal(parsePreview({...p,packageVersion:'1.0.0',workingRecordsExtension:null}).packageVersion,'1.0.0')
assert.throws(()=>parsePreview({...p,packageVersion:'1.3.0'}))
const r={...p,importedUtc:'2026-01-01T00:00:00Z',replayed:false}
assert.equal(parseReceipt(r,parsePreview(p)).replayed,false)
assert.throws(()=>parseReceipt({...r,workingRecordsExtension:{...w,reportCount:1}},parsePreview(p)))
const text=renderToStaticMarkup(<WorkingRecordsSummary extension={parsePreview(p).workingRecordsExtension}/>)
for(const word of ['仅同案号新案恢复','历史回执只读归档','不是本次签署或审核','整包拒绝','64 MiB','不会丢弃祖先'])assert.ok(text.includes(word))
assert.ok(renderToStaticMarkup(<WorkingRecordsSummary extension={null}/>).includes('完整性校验成功不等于'))
console.log('Archive B model: synthetic version/count/receipt/limitations checks passed')

}
main().catch(e=>{console.error(e);process.exit(1)})

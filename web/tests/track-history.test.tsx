import assert from 'node:assert/strict'
import {parsePreview,parseReceipt} from '../src/packageIntake/model'
const ext={version:'MCIS-WORKING-RECORDS-2',trackReceiptCount:1,interviewCount:0,reportCount:0,reportSnapshotCount:0,manualReceiptCount:0,receiptMode:'archive-only',identityMode:'unverified-self-reported'}
const p={profile:'MCIS-BASIC-INTAKE-1',caseId:'A',title:'Synthetic',sourceSha256:'a'.repeat(64),byteLength:10,packageVersion:'1.3.0',hfacsExtension:null,workingRecordsExtension:ext,counts:{},warnings:[]}
assert.equal(parsePreview(p).workingRecordsExtension?.trackReceiptCount,1)
for(const delta of [{trackReceiptCount:0},{trackReceiptCount:true},{trackReceiptCount:2049},{version:'MCIS-WORKING-RECORDS-1'},{unknown:1}])assert.throws(()=>parsePreview({...p,workingRecordsExtension:{...ext,...delta}}))
assert.throws(()=>parsePreview({...p,packageVersion:'1.2.0'}))
assert.throws(()=>parseReceipt({...p,importedUtc:'2026-01-01T00:00:00Z',replayed:false,workingRecordsExtension:{...ext,trackReceiptCount:2}},parsePreview(p)))
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null}})
const {parseHistory,historyRefusal}=await import('../src/trackInput/history')
const {ApiError}=await import('../src/api')
const h={caseId:'A',vesselId:'V',digest:'a'.repeat(64),mode:'archive-only',sourceEvidenceId:'E1',reportEvidenceId:'E2',sourceSha256:'b'.repeat(64),reportSha256:'c'.repeat(64),pointCount:2,identityMode:'unverified-self-reported'}
assert.equal(parseHistory(h,'A','V'),h)
for(const delta of [{caseId:'B'},{mode:'active'},{replayed:true},{sourceSha256:'x'},{pointCount:0},{reportEvidenceId:'E1'}])assert.throws(()=>parseHistory({...h,...delta},'A','V'))
assert.equal(historyRefusal(new ApiError(409,'ARCHIVE_HISTORY_ONLY','',null)),true)
assert.equal(historyRefusal(new ApiError(409,'TRACK_ORIGIN_UNVERIFIED','',null)),true)
assert.equal(historyRefusal(new ApiError(409,'OTHER','',null)),false)
console.log('track history 18 assertions passed')

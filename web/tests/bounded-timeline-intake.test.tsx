// Constructed response/model/SSR tests; not browser, SSO, or HFACS execution.
import {strict as assert} from 'node:assert'
import {readFileSync} from 'node:fs'
import {parsePreview,parseReceipt,type Preview} from '../src/packageIntake/model'
import {renderToStaticMarkup} from 'react-dom/server'
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
let checks=0
const reject=(value:unknown)=>{assert.throws(()=>parsePreview(value));checks++}
async function main(){
 const working={version:'MCIS-WORKING-RECORDS-1' as const,interviewCount:0,reportCount:1,reportSnapshotCount:0,manualReceiptCount:0,receiptMode:'archive-only' as const,identityMode:'unverified-self-reported' as const}
 const p:Preview={profile:'MCIS-BASIC-INTAKE-1',packageVersion:'1.4.0',workingRecordsExtension:working,hfacsExtension:null,caseId:'SYNTHETIC',title:'Synthetic only',sourceSha256:'a'.repeat(64),byteLength:1024,counts:{},warnings:[]}
 assert.equal(parsePreview(p).packageVersion,'1.4.0');checks++
 reject({code:'ARCHIVE_RESTORE_UNSUPPORTED',message:'Synthetic rejection'})
 reject({code:'PACKAGE_INTAKE_INVALID',message:'Synthetic unsupported combination'})
 for(const version of ['1.5.0','1.4','1.4.1',null,undefined])reject({...p,packageVersion:version})
 for(const w of [null,undefined,{...working,version:'MCIS-WORKING-RECORDS-2'},{...working,trackReceiptCount:1},{...working,receiptMode:'active'},{...working,identityMode:'authenticated'},{...working,unknown:true}])reject({...p,workingRecordsExtension:w})
 for(const [key,max] of Object.entries({interviewCount:128,reportCount:256,reportSnapshotCount:1024,manualReceiptCount:2048})){
  for(const n of [0,max]){parsePreview({...p,workingRecordsExtension:{...working,[key]:n}});checks++}
  for(const n of [-1,max+1,0.5,NaN,Infinity,'1'])reject({...p,workingRecordsExtension:{...working,[key]:n}})
 }
 const h={version:'MCIS-HFACS-PACKAGE-1',draftCount:1,revisionCount:1,receiptCount:1,receiptMode:'archive-only',identityMode:'unverified-self-reported'}
 parsePreview({...p,hfacsExtension:h});checks++
 reject({...p,hfacsExtension:{...h,receiptCount:2}})
 const receipt={...p,importedUtc:'2026-11-15T00:00:00Z',replayed:false}
 parseReceipt(receipt,p);checks++
 for(const changed of [{...receipt,packageVersion:'1.2.0'},{...receipt,sourceSha256:'b'.repeat(64)},{...receipt,counts:{reports:2}},{...receipt,workingRecordsExtension:{...working,reportCount:2}}]){assert.throws(()=>parseReceipt(changed,p));checks++}
 // Preserve previously supported versions, including v2 only with outer1.3.
 for(const version of ['1.0.0','1.1.0','1.2.0','1.3.0']){
  parsePreview({...p,packageVersion:version,hfacsExtension:version==='1.1.0'?h:null,workingRecordsExtension:version==='1.2.0'?working:version==='1.3.0'?{...working,version:'MCIS-WORKING-RECORDS-2',trackReceiptCount:1}:null});checks++
 }
 const {IntakeSummary,PackageIntakePanel}=await import('../src/packageIntake/PackageIntakePanel')
 const html=renderToStaticMarkup(<IntakeSummary preview={p}/>)+renderToStaticMarkup(<PackageIntakePanel who={'LeadInvestigator\nSynthetic'} onImported={()=>{}}/>)
 for(const label of ['1.4.0','时间线','航迹导入历史混合','安全建议','征求意见','避碰分析','智能体草稿','整包拒绝','不是通用案件恢复','不会提升权限']){assert.ok(html.includes(label),label);checks++}
 if(process.argv[2]){const real=JSON.parse(readFileSync(process.argv[2],'utf8'));parsePreview(real.preview);parseReceipt(real.receipt,real.preview);checks+=2}
 console.log(`${checks} bounded1.4 assertions passed; constructed/SSR${process.argv[2]?' + actual synthetic HTTP response':''}; browser not tested`)
}
main().catch(e=>{console.error(e);process.exit(1)})

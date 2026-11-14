import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {renderToStaticMarkup} from 'react-dom/server'
import {parsePreview,parseReceipt} from '../../web/src/packageIntake/model'
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
async function main(){
 const actual=JSON.parse(readFileSync(process.env.MCIS_REAL_TIMELINE_RESPONSES!,'utf8'));const p=parsePreview(actual.preview);let checks=0
 for(const extension of [null,undefined,[],{}, {...p.workingRecordsExtension,version:'MCIS-WORKING-RECORDS-2',trackReceiptCount:1},{...p.workingRecordsExtension,extra:true}]){assert.throws(()=>parsePreview({...p,workingRecordsExtension:extension}));checks++}
 for(const count of [-1,0.5,257,NaN,Infinity]){assert.throws(()=>parsePreview({...p,workingRecordsExtension:{...p.workingRecordsExtension,reportCount:count}}));checks++}
 for(const patch of [{caseId:'OTHER'},{byteLength:p.byteLength+1},{packageVersion:'1.2.0'},{sourceSha256:'f'.repeat(64)},{counts:{...p.counts,evidence:(p.counts.evidence??0)+1}}]){assert.throws(()=>parseReceipt({...actual.commit,...patch},p));checks++}
 const h={version:'MCIS-HFACS-PACKAGE-1',draftCount:1,revisionCount:1,receiptCount:1,receiptMode:'archive-only',identityMode:'unverified-self-reported'}
 for(const patch of [{receiptCount:2},{identityMode:'trusted'},{receiptMode:'active'},{version:'MCIS-HFACS-PACKAGE-2'},{unexpected:1}]){assert.throws(()=>parsePreview({...p,hfacsExtension:{...h,...patch}}));checks++}
 const {IntakeSummary}=await import('../../web/src/packageIntake/PackageIntakePanel')
 const html=renderToStaticMarkup(<IntakeSummary preview={{...p,title:'<script>synthetic</script>'}}/>);
 assert(!html.includes('<script>'));checks++;assert(html.includes('&lt;script&gt;'));checks++
 assert(html.includes('1.4.0 受限工作记录归档'));checks++;assert(!html.includes('航迹历史回执数'));checks++
 console.log(`${checks} independent real-response-derived mutation/SSR assertions passed; not browser interaction`)
}main().catch(e=>{console.error(e);process.exit(1)})

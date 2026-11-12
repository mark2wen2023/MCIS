import {strict as assert} from 'node:assert'
import {readRecoveries,rememberRecovery,forgetRecovery} from '../src/interviewIntake/locks'
const store=new Map<string,string>()
Object.defineProperty(globalThis,'sessionStorage',{value:{getItem:(k:string)=>store.get(k)??null,setItem:(k:string,v:string)=>store.set(k,v)},configurable:true})
const r={caseId:'synthetic',recordId:null,requestId:'11111111-1111-4111-8111-111111111111',operation:'create' as const}
assert.deepEqual(readRecoveries(),[]);rememberRecovery(r);assert.deepEqual(readRecoveries(),[r]);rememberRecovery(r);assert.equal(readRecoveries().length,1)
assert.throws(()=>rememberRecovery({...r,requestId:'22222222-2222-4222-8222-222222222222'}));assert.equal(readRecoveries().length,1)
assert.deepEqual(Object.keys(JSON.parse([...store.values()][0])[0]).sort(),['caseId','operation','recordId','requestId'])
forgetRecovery(r.requestId);assert.deepEqual(readRecoveries(),[])
store.set('mcis.manual-interview.pending.v1','bad json');assert.throws(readRecoveries)
store.set('mcis.manual-interview.pending.v1',JSON.stringify([{...r,answer:'must not persist'}]));assert.throws(readRecoveries)
console.log('W5.2b recovery metadata whitelist / unresolved lock / corrupt storage fail-closed passed (synthetic)')
import {parseDocument,parseReceipt,utc,text,PROFILE,BACKUP_WARNING} from '../src/interviewIntake/model'
assert(utc('2026-11-12T00:00:00Z'));for(const bad of ['2026-02-30T00:00:00Z','2026-11-12T00:00:00.1Z','','1899-01-01T00:00:00Z'])assert(!utc(bad))
assert.equal(text(' 原文\n','Q',20),' 原文\n');assert.throws(()=>text(' ','Q',20));assert.equal(text('😀','Q',1),'😀')
const d={profile:PROFILE,caseId:'C',record:{caseId:'C',recordId:'IR-01',interviewee:{intervieweeId:'I',name:'n',role:'r',affiliation:'a'},startUtc:'2026-11-12T00:00:00Z',turns:[],signed:false},documentDigest:'a'.repeat(64),sourceBinding:'none',signed:false,identityMode:'local-role-header'}
assert.equal(parseDocument(d,'C','IR-01').record.recordId,'IR-01');assert.throws(()=>parseDocument(d,'D','IR-01'));assert.throws(()=>parseDocument({...d,signed:true},'C','IR-01'))
const receipt={profile:PROFILE,caseId:'C',receipt:{requestId:r.requestId,operation:'create',recordId:'IR-01',beforeDigest:null,afterDigest:'a'.repeat(64),turnRound:null,appliedUtc:'2026-11-12T00:00:00Z'},currentDigest:'b'.repeat(64),sourceBinding:'none',identityMode:'local-role-header',replayed:true}
const expected={...r,caseId:'C'};assert.equal(parseReceipt(receipt,expected).currentDigest,'b'.repeat(64));assert.throws(()=>parseReceipt({...receipt,caseId:'OTHER'},expected));assert.throws(()=>parseReceipt({...receipt,receipt:{...receipt.receipt,requestId:'other'}},expected));assert(BACKUP_WARNING.includes('原始资料须独立保管'))
async function more(){
 Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}},configurable:true})
 const {ApiError}=await import('../src/api');const {packageError}=await import('../src/packages/api')
 const error=packageError(new ApiError(409,'INTERVIEW_RECEIPTS_BACKUP_UNSUPPORTED','',null));assert(error.includes('整个案件包导出已拒绝')&&error.includes('重试不能解决'))
 const {createElement}=await import('react');const {renderToStaticMarkup}=await import('react-dom/server');const {PackageExport}=await import('../src/packages/PackagePanel')
 const html=renderToStaticMarkup(createElement(PackageExport,{caseId:'C',title:'Synthetic',who:'LeadInvestigator\nTest'}));assert(html.includes('完整性校验成功不等于可恢复'))
 console.log('W5.2b UTC/text/binding/receipt/backup refusal+render passed (synthetic)')
}void more().catch(e=>{console.error(e);process.exitCode=1})

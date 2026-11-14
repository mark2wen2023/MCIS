/** Real Node fetch -> Vite proxy -> FastAPI -> actual W2, NOT a browser test. */
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
const storage=new Map<string,string>()
Object.assign(globalThis,{localStorage:{getItem:(k:string)=>storage.get(k)??null,setItem:(k:string,v:string)=>storage.set(k,v)}})
const base=new URL(process.env.MCIS_ACCEPTANCE_WEB_URL??'')
assert.equal(base.protocol,'http:');assert.equal(base.hostname,'127.0.0.1');assert.ok(base.port);assert.equal(base.pathname,'/')
const nativeFetch=globalThis.fetch
const observed:{status:number;cache:RequestCache|undefined}[]=[]
globalThis.fetch=async(input,init)=>{
  // Only URL resolution and observation; responses always originate from native network fetch.
  const response=await nativeFetch(new URL(String(input),base),init)
  observed.push({status:response.status,cache:init?.cache})
  return response
}
const {setIdentity,ApiError}=await import('../src/api')
const {caseIdentity}=await import('../src/cases/identity')
const {intakeRequest}=await import('../src/evidenceIntake/api')
const {registeredBody,registeredResult}=await import('../src/align/registered')
const caseId='CASE-2026-DEMO-LILY-MARY'
setIdentity('Investigator','network acceptance')
const request=(path:string,body?:unknown,signal=new AbortController().signal)=>intakeRequest(caseId,caseIdentity(),path,signal,body)
const ids:string[]=[]
for(const heading of [45,50]){
  const body={profile:'mcis-evidence-intake-v1',fileName:`fictional-${heading}.csv`,contentBase64:Buffer.from(`utc,heading\n2026-05-18T06:15:00Z,${heading}\n`).toString('base64'),title:'Fictional network test',source:'synthetic',extractedBy:'acceptance',extractedUtc:'2026-01-01T00:00:00Z',category:'AIS',confidentiality:'Restricted',note:''}
  const preview=await request('/evidence-intakes:preview',body) as any
  const receipt=await request('/evidence-intakes:commit',{...body,requestDigest:preview.requestDigest,confirmed:true}) as any
  ids.push(receipt.evidenceId)
}
const body=registeredBody(ids.map(evidenceId=>({evidenceId,timeColumn:'utc',column:'heading',kind:'Heading'})))
assert.deepEqual(Object.keys(body.sources[0]).sort(),['csvMapping','evidenceId'])
const legacy=registeredResult(await request('/timeline/registered-align-preview',body),caseId,ids)
assert.equal(legacy.comparisonScope?.status,'unscoped')
const scopedRows=ids.map(evidenceId=>({evidenceId,timeColumn:'utc',column:'heading',kind:'Heading' as const,comparisonContext:{vesselLabel:'Fictional vessel',sourceNature:'report_extract' as const,sourceTitle:'Synthetic acceptance report, not a real report',citation:'Synthetic table 1',timeBasis:'Synthetic UTC values; no clock correction',headingReference:'true' as const}}))
const scopedBody=registeredBody(scopedRows)
const result=registeredResult(await request('/timeline/registered-align-preview',scopedBody),caseId,ids,scopedRows)
assert.equal(result.comparisonScope?.status,'user_declared_not_verified')
assert.equal(result.result.conflicts[0].delta,5)
assert.equal(result.persisted,false)
assert.equal(result.observationApproval,'not_assessed')
assert.ok(observed.every(r=>r.cache==='no-store')) // Request option, NOT proof of browser cache behavior.
// Real public PDF + report-derived single VDR row, never raw telemetry.
const pdf=readFileSync(new URL('../../reports/yangze22/report.pdf',import.meta.url));
const reportSha='99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f';
assert.equal(createHash('sha256').update(pdf).digest('hex'),reportSha);
const review=JSON.parse(readFileSync(new URL('../../research/skills_timeline/public_report_visual_review.json',import.meta.url),'utf8'));
assert.equal(review.report.sha256,reportSha);
const observation=review.observations.find((o:any)=>o.headingReference==='true');
assert.equal(observation.headingDeg,48);assert.equal(observation.pdfPage,41);
const register=async(bytes:Buffer,fileName:string)=>{const b={profile:'mcis-evidence-intake-v1',fileName,contentBase64:bytes.toString('base64'),title:'Public report transport acceptance',source:'YANGZE22 single published report family; not original telemetry',extractedBy:'test transcription, not human approval',extractedUtc:'2026-11-13T00:00:00Z',category:'Document',confidentiality:'Restricted',note:'Test-only intake in disposable DEMO case'};const p=await request('/evidence-intakes:preview',b) as any;return await request('/evidence-intakes:commit',{...b,requestDigest:p.requestDigest,confirmed:true}) as any};
const parentReceipt=await register(pdf,'yangze22-public.pdf');
const extractReceipt=await register(Buffer.from(`utc,heading\n${observation.interpretationUtc},48\n`),'public-report-extract.csv');
const parentRows=[{evidenceId:extractReceipt.evidenceId,timeColumn:'utc',column:'heading',kind:'Heading' as const,parentReport:{evidenceId:parentReceipt.evidenceId,sourceSha256:reportSha},comparisonContext:{vesselLabel:'YANGZE22 IMO9958212',sourceNature:'report_extract' as const,sourceTitle:'YANGZE22 public report',citation:'PDF page41 figure27; report-derived',timeBasis:observation.interpretationBasis,headingReference:'true' as const}}];
const linked=registeredResult(await request('/timeline/registered-align-preview',registeredBody(parentRows)),caseId,[extractReceipt.evidenceId],parentRows);
assert.equal(linked.reportSnapshots?.[0].sourceSha256,reportSha);
assert.equal(linked.reportSnapshots?.[0].relationshipStatus,'user_declared_not_verified');
assert.equal(linked.result.conflicts.length,0);assert.equal(linked.persisted,false);assert.equal(linked.observationApproval,'not_assessed');
const wrong=structuredClone(parentRows);wrong[0].parentReport.sourceSha256='f'.repeat(64);
await assert.rejects(()=>request('/timeline/registered-align-preview',registeredBody(wrong)),(e:any)=>e instanceof ApiError&&e.status===409);
setIdentity('AgentService','network denial')
await assert.rejects(()=>request('/timeline/registered-align-preview',body),(e:any)=>e instanceof ApiError&&e.status===403)
assert.equal(observed.at(-1)?.status,403)
assert.equal(observed.length,13)
assert.ok(observed.every(r=>r.cache==='no-store'))
setIdentity('Investigator','network cancellation')
const stopped=new AbortController();stopped.abort()
const count=observed.length
await assert.rejects(()=>request('/timeline/registered-align-preview',body,stopped.signal),(e:any)=>e.name==='AbortError')
assert.equal(observed.length,count)
console.log(JSON.stringify({transport:'native fetch -> Vite proxy -> FastAPI -> actual W2',requests:observed.length,delta:5,denial:403,preDispatchAbort:true,noStoreRequestOption:true,browserVerified:false,parentReportNativeTransport:true,publicReportSingleSourceNotCorroboration:true}))

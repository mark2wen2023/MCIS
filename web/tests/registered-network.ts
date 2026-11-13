/** Real Node fetch -> Vite proxy -> FastAPI -> actual W2, NOT a browser test. */
import assert from 'node:assert/strict'
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
setIdentity('AgentService','network denial')
await assert.rejects(()=>request('/timeline/registered-align-preview',body),(e:any)=>e instanceof ApiError&&e.status===403)
assert.equal(observed.at(-1)?.status,403)
assert.equal(observed.length,7)
assert.ok(observed.every(r=>r.cache==='no-store'))
setIdentity('Investigator','network cancellation')
const stopped=new AbortController();stopped.abort()
const count=observed.length
await assert.rejects(()=>request('/timeline/registered-align-preview',body,stopped.signal),(e:any)=>e.name==='AbortError')
assert.equal(observed.length,count)
console.log(JSON.stringify({transport:'native fetch -> Vite proxy -> FastAPI -> actual W2',requests:observed.length,delta:5,denial:403,preDispatchAbort:true,noStoreRequestOption:true,browserVerified:false}))

import { strict as assert } from 'node:assert'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { MAX_BYTES,fileError,encodeBytes,parsePreview,parseReceipt } from '../src/packageIntake/model'
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
const p={profile:'MCIS-BASIC-INTAKE-1',caseId:'ABC',title:'<script>x</script>',sourceSha256:'a'.repeat(64),byteLength:12,counts:{evidence:2},warnings:['人工核对']}
assert.equal(MAX_BYTES,33554432);assert.equal(fileError({name:'x.mcase',size:MAX_BYTES}),null)
for(const f of [{name:'x.zip',size:1},{name:'x.mcase',size:0},{name:'x.mcase',size:MAX_BYTES+1}])assert.ok(fileError(f))
assert.equal(encodeBytes(new Uint8Array([0,255,13,10])),'AP8NCg==')
assert.deepEqual(parsePreview(p),p)
for(const patch of [{profile:'unknown'},{sourceSha256:'A'.repeat(64)},{byteLength:0},{counts:{n:-1}},{warnings:[2]}])assert.throws(()=>parsePreview({...p,...patch}))
const receipt={...p,importedUtc:'2026-11-12T00:00:00Z',replayed:false}
assert.equal(parseReceipt(receipt,p).caseId,'ABC')
for(const patch of [{caseId:'OTHER'},{sourceSha256:'b'.repeat(64)},{counts:{evidence:3}},{replayed:'true'},{importedUtc:'invalid'}])assert.throws(()=>parseReceipt({...receipt,...patch},p))
async function main(){
 const { IntakeSummary,PackageIntakePanel }=await import('../src/packageIntake/PackageIntakePanel')
 const html=renderToStaticMarkup(<IntakeSummary preview={p}/>);assert.ok(html.includes('&lt;script&gt;'));assert.ok(!html.includes('<script>'));assert.ok(html.includes('不代表来源真实'))
 assert.equal(renderToStaticMarkup(<MemoryRouter><PackageIntakePanel who={'Viewer\nx'} onImported={()=>{}}/></MemoryRouter>),'')
 const panel=renderToStaticMarkup(<MemoryRouter><PackageIntakePanel who={'Investigator\n调查员 A'} onImported={()=>{}}/></MemoryRouter>);assert.ok(panel.includes('不是完整案件包还原'));assert.ok(panel.includes('不静默丢弃'))
 const { request }=await import('../src/packageIntake/api');const calls:any[]=[]
 globalThis.fetch=async (u,o)=>{calls.push({u,o});return new Response(JSON.stringify(p))}
 const who='Investigator\n调查员 A',c=new AbortController()
 await request(who,':preview',c.signal,{contentBase64:'AA=='});assert.equal(calls[0].o.signal,c.signal);assert.equal(calls[0].o.method,'POST')
 await request(who,':commit',c.signal,{confirmed:true});assert.equal(calls[1].o.signal,undefined)
 await request(who,'/'+p.sourceSha256,c.signal);assert.equal(calls[2].o.method,'GET');assert.equal(calls[2].o.body,undefined)
 await assert.rejects(()=>request('stale',':commit',c.signal,{}));assert.equal(calls.length,3)
 c.abort();await assert.rejects(()=>request(who,':commit',c.signal,{}));assert.equal(calls.length,3)
 globalThis.fetch=async()=>new Response('',{status:409});await assert.rejects(()=>request(who,':preview',new AbortController().signal,{}))
 console.log('W8.5 frontend model, render and transport tests passed')
}
main().catch(e=>{console.error(e);process.exit(1)})

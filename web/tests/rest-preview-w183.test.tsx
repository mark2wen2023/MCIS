import {strict as assert} from 'node:assert'
import {renderToStaticMarkup} from 'react-dom/server'
import {PROFILE,canonicalInput,inputHash,verifySourceSnapshot,parsePreview,parseSources,validateInput,utcSeconds,type Input,type Preview} from '../src/humanFactorsPreview/model'
import {RestResult} from '../src/humanFactorsPreview/Result'
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
const input:Input={recordStartUtc:'2026-11-12T00:00:00Z',recordEndUtc:'2026-11-13T00:00:00Z',intervals:[{startUtc:'2026-11-12T00:00:00Z',endUtc:'2026-11-12T08:00:00Z',kind:'Rest'}],sourceEvidenceIds:['E1']}
const sources=[{evidenceId:'E1',title:'<img src=x>',sha256:'a'.repeat(64)}]
const preview:Preview={profile:PROFILE,caseId:'A',inputSha256:'b'.repeat(64),sources,sourceBinding:'registered-metadata-only',persisted:false,assessment:'technical-preview-only',result:{coreVersion:'mcis-rest/1',mode:'rest-baseline-no-exceptions',totals:{restHours:8,workHours:0,unknownHours:16},coverage:{recordHours:24,has24hWindow:true,has7dWindow:false,unknownHours:16},findings:[],insufficientData:[],assumptions:['project assumption']},limitations:['not legal advice']}
verifySourceSnapshot(sources,sources);for(const patch of [{title:'changed'},{sha256:'c'.repeat(64)},{evidenceId:'E2'}])assert.throws(()=>verifySourceSnapshot([{...sources[0],...patch}],sources));assert.throws(()=>verifySourceSnapshot([],sources));
validateInput(input);assert.ok(!utcSeconds('2026-02-30T00:00:00Z'));assert.ok(!utcSeconds('2026-11-12T00:00:00+00:00'))
for(const patch of [{recordStartUtc:''},{sourceEvidenceIds:[]},{sourceEvidenceIds:['E1','E1']},{recordEndUtc:'2026-12-12T00:00:00Z'},{intervals:[]},{intervals:[...input.intervals,...input.intervals]}])assert.throws(()=>validateInput({...input,...patch}))
assert.equal(parsePreview(preview,'A',input,preview.inputSha256,sources).result.totals.unknownHours,16)
for(const patch of [{persisted:true},{caseId:'B'},{sources:[]},{result:{...preview.result,mode:'work-limits'}},{result:{...preview.result,coverage:{...preview.result.coverage,has7dWindow:true}}}])assert.throws(()=>parsePreview({...preview,...patch},'A',input,preview.inputSha256,sources))
assert.deepEqual(parseSources({profile:PROFILE,caseId:'A',sources,sourceBinding:'registered-metadata-only'},'A'),sources)
assert.throws(()=>parseSources({profile:PROFILE,caseId:'B',sources,sourceBinding:'registered-metadata-only'},'A'))
assert.throws(()=>parsePreview(preview,'A',input,'f'.repeat(64),sources));assert.ok(canonicalInput('A',input,sources).startsWith('{"caseId":"A","schedule":'));
const html=renderToStaticMarkup(<RestResult preview={preview}/>);assert.ok(html.includes('&lt;img'));assert.ok(html.includes('未知小时'));assert.ok(html.includes('记录长度不足'));assert.ok(html.includes('不代表合规'));assert.ok(html.includes('未保存'))
async function main(){assert.match(await inputHash('A',input,sources),/^[a-f0-9]{64}$/);const {restRequest,restError}=await import('../src/humanFactorsPreview/api');const {ApiError}=await import('../src/api');const calls:any[]=[];globalThis.fetch=async(u,o)=>{calls.push({u,o});return new Response(JSON.stringify(preview))};const c=new AbortController();await restRequest('A /中','Investigator\n调查员 A','preview',c.signal,input);assert.equal(calls[0].o.method,'POST');assert.equal(calls[0].o.cache,'no-store');assert.equal(calls[0].o.signal,c.signal);assert.ok(calls[0].u.includes('A%20%2F%E4%B8%AD'));await assert.rejects(()=>restRequest('A','stale','preview',c.signal,input));assert.equal(calls.length,1);assert.ok(restError(new ApiError(503,'','',null)).includes('不会用示例结果'));console.log('W18.3 input/model/render/transport tests passed')}
main().catch(e=>{console.error(e);process.exit(1)})

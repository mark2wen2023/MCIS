import {strict as assert} from 'node:assert'
import {renderToStaticMarkup} from 'react-dom/server'
import {emptyParameters,validateParameters,parsePreview,canonicalInput,inputHash,type Preview,type Point} from '../src/nomotoPreview/model'
import {NomotoResult,trajectoryBounds} from '../src/nomotoPreview/Result'
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
const p={...emptyParameters(),headingDeg:'0',speedKn:'0',k:'0.1',tSeconds:'10',referenceSpeedKn:'5',maxRudderDeg:'35',rudderRateDegPerSec:'2',commandRudderDeg:'10',durationSeconds:'1',provenanceNote:'Synthetic',uncertaintyNote:'Uncalibrated'}
assert.ok(Object.values(emptyParameters()).every(x=>x===''));validateParameters(p)
for(const patch of [{k:'1e-2'},{speedKn:'-0'},{speedKn:'01'},{headingDeg:'360'},{durationSeconds:'1.0'},{provenanceNote:''},{commandRudderDeg:'36'},{speedKn:'40',referenceSpeedKn:'1'}])assert.throws(()=>validateParameters({...p,...patch}))
const point:Point={timeSeconds:0,eastM:0,northM:0,headingDeg:0,speedKn:0,rotDegPerSec:0,rudderDeg:0};const preview:Preview={profile:'MCIS-NOMOTO-PREVIEW-1',caseId:'A',inputSha256:'a'.repeat(64),sources:[],sourceRole:'Investigator',sourceBinding:'registered-metadata-only',persisted:false,assessment:'hypothetical-single-vessel-response',result:{coreVersion:'mcis-nomoto/1',mode:'fixed-rudder-hypothesis',stepSeconds:.1,comparisonStepSeconds:.05,baseline:[point,{...point,timeSeconds:1}],response:[point,{...point,timeSeconds:1,rudderDeg:2}],numericalDifference:{endpointDistanceM:0,endpointHeadingDifferenceDeg:0,endpointRotDifferenceDegPerSec:0},assumptions:['synthetic']},limitations:['synthetic']}
parsePreview(preview,'A','Investigator\nx',p,preview.inputSha256,[])
for(const patch of [{inputSha256:'b'.repeat(64)},{persisted:true},{result:{...preview.result,response:[point]}},{result:{...preview.result,baseline:[{...point,eastM:1},{...point,timeSeconds:1}]}}])assert.throws(()=>parsePreview({...preview,...patch},'A','Investigator\nx',p,preview.inputSha256,[]))
assert.notEqual(canonicalInput('A',p,[]),canonicalInput('A',{...p,k:'0.10'},[]));assert.ok(trajectoryBounds([point]).span>0)
const html=renderToStaticMarkup(<NomotoResult preview={preview}/>);assert.ok(html.includes('两条均不是实测'));assert.ok(html.includes('不是置信区间'));assert.ok(html.includes('实际舵角'));assert.ok(html.includes('X/Y等比例'))
async function main(){assert.match(await inputHash('A',p,[]),/^[a-f0-9]{64}$/);const {nomotoRequest}=await import('../src/nomotoPreview/api');const calls:any[]=[];globalThis.fetch=async(u,o)=>{calls.push({u,o});return new Response('{}')};await nomotoRequest('A','Investigator\n调查员 A','preview',new AbortController().signal,{parameters:p,sourceEvidenceIds:[]});assert.equal(calls[0].o.cache,'no-store');assert.equal(JSON.parse(calls[0].o.body).parameters.k,'0.1');assert.equal(calls[0].o.method,'POST');console.log('W14.4 model/render/transport tests passed')}
main().catch(e=>{console.error(e);process.exit(1)})

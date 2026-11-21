import {strict as assert} from 'node:assert'
import {renderToStaticMarkup} from 'react-dom/server'
import {readFileSync} from 'node:fs'
import {canonicalInput,PROFILE,parsePreview,type Input,type Node} from '../src/bowtiePreview/model'
import {currentPathWitnesses,type ReviewedPreview} from '../src/bowtiePreview/pathWitnesses'
import {UnprotectedPaths} from '../src/bowtiePreview/UnprotectedPaths'
const who='Investigator\nSynthetic',caseId='SYN-CASE-A'
const node=(id:string,kind:Node['kind']):Node=>({id,label:'Synthetic '+id,kind,barrierId:null})
function input(nodes:Node[],edges:string[][]):Input{return {model:{hazard:'Synthetic hazard',topEvent:{id:'TOP',label:'Synthetic top'},nodes,edges:edges.map(([fromId,toId])=>({fromId:fromId!,toId:toId!}))},sourceEvidenceIds:[]}}
// Synthetic structure response only, no core/service execution or authorization.
function accepted(i:Input):ReviewedPreview{return {profile:PROFILE,caseId,reviewedIdentity:who,inputSha256:'a'.repeat(64),reviewedInput:canonicalInput(caseId,i.model,[]),sources:[],sourceRole:'Investigator',sourceBinding:'registered-metadata-only',persisted:false,assessment:'hypothesis-structure-only',result:{coreVersion:'mcis-bowtie/1',mode:'hypothesis-structure-only',constructionErrors:[],validationIssues:[],structureValid:true,notCheckedRefCount:0,nodeCount:i.model.nodes.length+1,edgeCount:i.model.edges.length},limitations:[]}}
const read=(i:Input,r=accepted(i))=>currentPathWitnesses(i,r,caseId,who,[])
const ids=(i:Input)=>read(i)!.map(p=>p.nodes.map(n=>n.id))
const direct=input([node('T','Threat'),node('C','Consequence')],[['T','TOP'],['TOP','C']])
assert.deepEqual(ids(direct),[['T','TOP'],['TOP','C']])
const chain=input([node('T','Threat'),node('A','Threat'),node('B','Threat')],[['T','B'],['T','A'],['B','TOP'],['A','TOP']])
assert.deepEqual(ids(chain),[['A','TOP'],['B','TOP'],['T','A','TOP']])
const reordered=structuredClone(chain);reordered.model.nodes.reverse();reordered.model.edges.reverse();assert.deepEqual(ids(reordered),ids(chain))
const blocked=input([node('T','Threat'),node('P','PreventionBarrier'),node('M','MitigationBarrier'),node('C','Consequence')],[['T','P'],['P','TOP'],['TOP','M'],['M','C']])
assert.deepEqual(ids(blocked),[])
const both=structuredClone(blocked);both.model.edges.push({fromId:'T',toId:'TOP'},{fromId:'TOP',toId:'C'});assert.deepEqual(ids(both),ids(direct))
const original=accepted(direct),edited=structuredClone(direct);edited.model.nodes[0]!.label='Edited'
assert.equal(read(edited,original),null)
assert.equal(currentPathWitnesses(direct,original,'SYN-CASE-B',who,[]),null)
assert.equal(currentPathWitnesses(direct,original,caseId,'Investigator\nOther synthetic',[]),null)
assert.equal(currentPathWitnesses(direct,original,caseId,'Public\nSynthetic',[]),null)
assert.equal(currentPathWitnesses(direct,original,caseId,who,[],true),null)
assert.equal(currentPathWitnesses(direct,null,caseId,who,[]),null)
assert.equal(read(direct,{...original,result:{...original.result,structureValid:false}}),null)
assert.equal(read(direct,{...original,result:{...original.result,nodeCount:2}}),null)
assert.equal(read(direct,{...original,reviewedInput:'old'}),null)
assert.throws(()=>parsePreview({...original,inputSha256:'b'.repeat(64)},caseId,who,direct,'a'.repeat(64),[]))
const duplicate=structuredClone(direct);duplicate.model.nodes.push(node('T','Threat'));assert.equal(read(duplicate),null)
const missing=structuredClone(direct);missing.model.edges.push({fromId:'missing',toId:'TOP'});assert.equal(read(missing),null)
const oversized=structuredClone(direct);oversized.model.nodes=Array.from({length:65},(_,i)=>node('T'+i,'Threat'));assert.equal(read(oversized),null)
const sourceInput=structuredClone(direct);sourceInput.sourceEvidenceIds=['E'];const src={evidenceId:'E',title:'Synthetic',sha256:'c'.repeat(64)}
const sourced={...accepted(sourceInput),sources:[src],reviewedInput:canonicalInput(caseId,sourceInput.model,[src])}
assert.ok(currentPathWitnesses(sourceInput,sourced,caseId,who,[src]))
assert.equal(currentPathWitnesses(sourceInput,sourced,caseId,who,[{...src,sha256:'d'.repeat(64)}]),null)
const escaped=structuredClone(direct);escaped.model.nodes[0]!.label='<img onerror=synthetic>'
const html=renderToStaticMarkup(<UnprotectedPaths paths={read(escaped)}/>)
assert.match(html,/aria-labelledby="w153-path-heading"/);assert.match(html,/<ul>/);assert.match(html,/未画预防屏障/);assert.match(html,/未画减缓屏障/);assert.match(html,/&lt;img/);assert.ok(!html.includes('<img'))
assert.match(html,/不表示现实中没有屏障/);assert.match(html,/Synthetic top/);assert.match(html,/<code>T<\/code>/)
assert.equal(renderToStaticMarkup(<UnprotectedPaths paths={null}/>),'')
assert.match(renderToStaticMarkup(<UnprotectedPaths paths={[]}/>),/不代表控制充分/)
// Limited source wiring checks, not React effect/reconciliation execution.
const form=readFileSync('src/bowtiePreview/BowtieForm.tsx','utf8'),page=readFileSync('src/pages/SystemicPage.tsx','utf8')
assert.match(form,/setResult\(null\)/);assert.match(form,/const edit=.*clear\(\);setInput/)
assert.match(form,/parsePreview\(raw,caseId,who,input,hash,selected\)/)
assert.match(form,/currentPathWitnesses\(input,result,caseId,who,sources,stale\)/)
assert.match(page,/Session key=\{JSON.stringify\(\[caseId,who\]\)\}/)
console.log('PASS Bow-tie witnesses: direct, chains, barriers, alternatives, ordering, bounded invalid/stale/source cases and accessible SSR; wiring static only')

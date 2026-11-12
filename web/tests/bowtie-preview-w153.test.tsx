import {strict as assert} from 'node:assert'
import {renderToStaticMarkup} from 'react-dom/server'
import {PROFILE,inputHash,parsePreview,parseSources,validateInput,type Input,type Preview} from '../src/bowtiePreview/model'
import {Diagram} from '../src/bowtiePreview/Diagram'
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
const input:Input={model:{hazard:'Synthetic hazard',topEvent:{id:'TOP',label:'<img onerror=x>'},nodes:[{id:'T',label:'Threat',kind:'Threat',barrierId:null},{id:'C',label:'Consequence',kind:'Consequence',barrierId:null}],edges:[{fromId:'T',toId:'TOP'},{fromId:'TOP',toId:'C'}]},sourceEvidenceIds:[]}
validateInput(input);validateInput({...input,model:{...input.model,nodes:[...input.model.nodes,input.model.nodes[0]!]}})
assert.throws(()=>validateInput({...input,model:{...input.model,hazard:''}}));assert.throws(()=>validateInput({...input,model:{...input.model,nodes:[{...input.model.nodes[0]!,barrierId:'TOP'}]}}))
const preview:Preview={profile:PROFILE,caseId:'A',inputSha256:'a'.repeat(64),sources:[],sourceRole:'Investigator',sourceBinding:'registered-metadata-only',persisted:false,assessment:'hypothesis-structure-only',result:{coreVersion:'mcis-bowtie/1',mode:'hypothesis-structure-only',constructionErrors:[],validationIssues:[],structureValid:true,notCheckedRefCount:0,nodeCount:3,edgeCount:2},limitations:['Synthetic']}
parsePreview(preview,'A','Investigator\n调查员 A',input,preview.inputSha256,[])
for(const patch of [{inputSha256:'b'.repeat(64)},{caseId:'B'},{sourceRole:'Public'},{persisted:true},{result:{...preview.result,nodeCount:2}},{result:{...preview.result,structureValid:false}}])assert.throws(()=>parsePreview({...preview,...patch},'A','Investigator\n调查员 A',input,preview.inputSha256,[]))
assert.throws(()=>parsePreview(preview,'A','Investigator\n调查员 A',input,preview.inputSha256,[{evidenceId:'E',title:'x',sha256:'c'.repeat(64)}]))
assert.deepEqual(parseSources({profile:PROFILE,caseId:'A',sources:[],sourceBinding:'registered-metadata-only',identityMode:'local-role-header'},'A'),[])
const html=renderToStaticMarkup(<Diagram model={input.model}/>);assert.ok(html.includes('&lt;img'));assert.ok(html.includes('非已验证因果'));assert.ok(!html.includes('<img'))
async function main(){const {bowtieRequest}=await import('../src/bowtiePreview/api');assert.match(await inputHash('A',input.model,[]),/^[a-f0-9]{64}$/);const calls:any[]=[];globalThis.fetch=async(u,o)=>{calls.push({u,o});return new Response('{}')};const c=new AbortController();await bowtieRequest('A /中','Investigator\n调查员 A','preview',c.signal,input);assert.equal(calls[0].o.method,'POST');assert.equal(calls[0].o.cache,'no-store');assert.equal(calls[0].o.signal,c.signal);assert.ok(calls[0].u.includes('/systemic/bowtie:preview'));await assert.rejects(()=>bowtieRequest('A','stale','preview',c.signal,input));assert.equal(calls.length,1);console.log('W15.3 model/render/transport tests passed')}
main().catch(e=>{console.error(e);process.exit(1)})

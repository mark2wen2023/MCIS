// Read frozen workbench Git blobs; no checkout, merge, model call, or network.
import {execFileSync} from 'node:child_process'
import {readFileSync} from 'node:fs'
import path from 'node:path'
import {createHash} from 'node:crypto'
import {build} from '../../web/node_modules/esbuild/lib/main.js'
const REF='872815c240b6b709d8a1b1182d252ffe28ceca92'
const blobs={}
function source(name){
 if(!/^(research\/expert_workbench\/|research\/expert_group\/public-packet.json$|web\/src\/reportOutput\/strictJson.ts$)/.test(name)||name.includes('..'))throw Error('probe source scope')
 const raw=execFileSync('git',['show',REF+':'+name]);blobs[name]=createHash('sha256').update(raw).digest('hex');return raw.toString('utf8')
}
const plugin={name:'frozen-git',setup(b){
 b.onResolve({filter:/.*/},args=>{
  let name=args.kind==='entry-point'?args.path:path.posix.normalize(path.posix.join(path.posix.dirname(args.importer),args.path))
  if(!path.posix.extname(name))name+='.ts'
  return {path:name,namespace:'frozen-git'}
 })
 b.onLoad({filter:/.*/,namespace:'frozen-git'},args=>({contents:source(args.path),loader:args.path.endsWith('.json')?'json':'ts'}))
}}
async function module(name){const b=await build({entryPoints:['research/expert_workbench/'+name+'.ts'],plugins:[plugin],bundle:true,write:false,format:'esm',platform:'browser'});return import('data:text/javascript;base64,'+Buffer.from(b.outputFiles[0].text).toString('base64'))}
const {parseResult}=await module('model'),{mount}=await module('app')
const input=JSON.parse(readFileSync(0,'utf8')),bytes=v=>new TextEncoder().encode(JSON.stringify(v))
const report={workbenchCommit:REF,blobs,legacyAccepted:false,newReceiptAccepted:false,meetingAccepted:false,bridgeAccepted:false,contradictoryRemotePartialAccepted:false}
for(const [key,value] of [['legacyAccepted',input.legacy],['newReceiptAccepted',input.receipt],['meetingAccepted',input.receipt.meetingSnapshot],['bridgeAccepted',input.receipt.bridgeAudit],['contradictoryRemotePartialAccepted',input.contradiction]]){
 try{parseResult(bytes(value));report[key]=true}catch{}
}
const {Window}=await import(process.env.MCIS_HAPPY_DOM_MODULE||'/tmp/mcis-ui-deps/node_modules/happy-dom/lib/index.js')
const win=new Window();globalThis.document=win.document;let requests=0;globalThis.fetch=async()=>{requests++;throw Error('network prohibited')}
const root=document.createElement('main');document.body.append(root);mount(root)
const file=root.querySelector('input')
async function load(value){const raw=bytes(value);Object.defineProperty(file,'files',{configurable:true,value:[{size:raw.length,arrayBuffer:async()=>raw.buffer}]});file.dispatchEvent(new win.Event('change'));await new Promise(r=>setTimeout(r,0))}
await load(input.legacy);const prior=root.textContent
await load(input.receipt)
report.failedMeetingLoadPreservesLegacy=root.textContent.includes('此前结果保留')&&root.textContent.includes(input.legacy.runId)&&root.querySelectorAll('.card').length===2
report.legacyWasVisible=prior.includes(input.legacy.runId)&&prior.includes('脚本模拟')
report.constructedClaimLabelPresent=prior.includes('人工编写测试主张（含反例）')
report.fixedCitationPanelPresent=!!root.querySelector('[aria-label="固定报告引用"]')
report.networkCalls=requests
await win.happyDOM.close()
process.stdout.write(JSON.stringify(report))

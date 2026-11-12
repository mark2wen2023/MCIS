import { renderToStaticMarkup } from 'react-dom/server'
import { PROFILE,MAX_FILE_BYTES,intakeBody,parsePreview,parseReceipt,utcSeconds,fileNameValid,encodeBytes,sameMetadata,type Metadata } from '../src/evidenceIntake/model'
let n=0;const check=(v:unknown,label:string)=>{if(!v)throw Error(label);n++};const reject=(fn:()=>unknown)=>{let yes=false;try{fn()}catch{yes=true}check(yes,'invalid value must reject')}
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
const metadata:Metadata={title:' original <img src=x onerror=alert(1)> ',source:' source\n  transfer ',extractedBy:' Person ',extractedUtc:'2020-02-29T12:34:56Z',category:'Document',confidentiality:'Restricted',note:' original\n  note '}
const body=intakeBody('原件.txt','',metadata)
check(body.contentBase64===''&&body.note===metadata.note&&body.source===metadata.source&&body.title===metadata.title,'empty bytes allowed and original metadata not trimmed')
check(MAX_FILE_BYTES===8*1024*1024,'engineering file cap')
check(encodeBytes(new Uint8Array())==='','empty file encodes empty');check(encodeBytes(new Uint8Array([0,255,13,10]))==='AP8NCg==','bytes intact')
for(const x of ['', '.', '..','a/b','a:b','a\\b','x\u0000y','a'.repeat(129)])check(!fileNameValid(x),'unsafe filename rejected')
check(fileNameValid('原件 1.pdf'),'unicode basename valid')
for(const x of ['2020-02-29T12:34:56Z','1000-01-01T00:00:00Z','9999-12-31T23:59:59Z'])check(utcSeconds(x),'whole known UTC valid')
for(const x of ['', '0001-01-01T00:00:00Z','0999-01-01T00:00:00Z','2020-02-30T00:00:00Z','2021-02-29T00:00:00Z','2020-01-01T00:00Z','2020-01-01T00:00:00.001Z','2020-01-01T00:00:00+00:00','2020-01-01T24:00:00Z'])check(!utcSeconds(x),'invalid or imprecise time rejected')
for(const d of [{title:' '},{title:'t'.repeat(1001)},{source:''},{extractedBy:'p'.repeat(201)},{extractedUtc:''},{confidentiality:'Normal'},{category:'auto'},{note:'n'.repeat(2001)}])reject(()=>intakeBody('raw.bin','AA==',{...metadata,...d} as Metadata))
const preview={profile:PROFILE,caseId:'C',requestDigest:'a'.repeat(64),sourceSha256:'b'.repeat(64),fileName:body.fileName,byteLength:0,metadata,warnings:['human declarations only']}
const local={sha:preview.sourceSha256,size:0}
check(parsePreview(preview,'C',body,local).byteLength===0,'zero bytes preview valid')
for(const d of [{profile:'bad'},{caseId:'other'},{requestDigest:'bad'},{sourceSha256:'c'.repeat(64)},{fileName:'changed'},{byteLength:1},{byteLength:-1},{byteLength:MAX_FILE_BYTES+1},{metadata:{...metadata,note:'changed'}},{warnings:[{}]},{metadata:{...metadata,unexpected:'x'}}])reject(()=>parsePreview({...preview,...d},'C',body,local))
const receipt={caseId:'C',evidenceId:'EV-001',requestDigest:preview.requestDigest,sourceSha256:preview.sourceSha256,fileName:preview.fileName,byteLength:0,metadata,registeredUtc:'2026-11-12T00:00:00Z',registeredBy:'Registrar',registeredRole:'Investigator',replayed:false,evidence:{...metadata,caseId:'C',evidenceId:'EV-001',sha256:preview.sourceSha256,status:'Unverified',accessCount:0}}
check(parseReceipt(receipt,'C',preview).metadata.extractedUtc!==receipt.registeredUtc,'registration/extraction separate')
check(parseReceipt({...receipt,evidence:{...receipt.evidence,note:'later note edit'}},'C',preview).metadata.note===metadata.note,'original note retained despite legal current note edit')
for(const d of [{caseId:'other'},{evidenceId:'bad'},{requestDigest:'c'.repeat(64)},{sourceSha256:'c'.repeat(64)},{fileName:'../bad'},{byteLength:1},{metadata:{...metadata,title:'changed'}},{registeredUtc:'bad'},{registeredBy:''},{registeredRole:'Public'},{registeredRole:['Investigator']},{replayed:'false'},{evidence:{...receipt.evidence,caseId:'wrong'}},{evidence:{...receipt.evidence,sha256:'bad'}},{evidence:{...receipt.evidence,status:'Authentic'}},{evidence:{...receipt.evidence,status:['Unverified']}},{evidence:{...receipt.evidence,accessCount:-1}}])reject(()=>parseReceipt({...receipt,...d},'C',preview))
reject(()=>parseReceipt(receipt,'C',undefined,'EV-002'));check(sameMetadata(metadata,{...metadata}),'metadata comparison key based')
async function main(){
 const {EvidenceIntakePanel,Declaration}=await import('../src/evidenceIntake/EvidenceIntakePanel');const {setIdentity}=await import('../src/api')
 let html=renderToStaticMarkup(<EvidenceIntakePanel caseId="C" who={'Investigator\n调查员 A'} selectedEvidenceId="EV-001"/>);check(html.includes('登记已有文件副本'),'closed entry real scope');check(!html.includes('已核对登记回执'),'no fake initial success')
 html=renderToStaticMarkup(<Declaration metadata={metadata}/>);check(!html.includes('<img'),'source escaped');check(html.includes('&lt;img'),'escaped literal retained');check(html.includes('提取 UTC'),'extraction label')
 setIdentity('Public');html=renderToStaticMarkup(<EvidenceIntakePanel caseId="C" who="Public\n调查员 A"/>);check(!html.includes('<button')&&html.includes('仅向调查组'),'restricted role hidden');setIdentity('Investigator')
 const {intakeRequest}=await import('../src/evidenceIntake/api');const calls:any[]=[];globalThis.fetch=async(u,o)=>{calls.push({u,o});return new Response(JSON.stringify(preview))}
 await intakeRequest('C /甲','Investigator\n调查员 A','/evidence-intakes:preview',new AbortController().signal,body);check(calls[0].u==='/api/v1/cases/C%20%2F%E7%94%B2/evidence-intakes:preview','encoded case');check(calls[0].o.method==='POST','explicit preview post');check(JSON.parse(calls[0].o.body).contentBase64==='','zero byte preserved')
 await intakeRequest('C','Investigator\n调查员 A','/evidence/EV-001/intake',new AbortController().signal);check(calls[1].o.method==='GET','receipt read only');let denied=false;try{await intakeRequest('C','stale','/evidence-intakes:commit',new AbortController().signal,body)}catch{denied=true}check(denied&&calls.length===2,'stale identity no fetch')
 globalThis.fetch=async(u,o)=>{calls.push({u,o});return new Response(new Uint8Array([0,255]),{headers:{'X-Sha256':'a'.repeat(64)}})};const raw=await intakeRequest('C','Investigator\n调查员 A','/evidence-intakes/d:download',new AbortController().signal,{purpose:' original purpose '},true) as {bytes:ArrayBuffer;sha:string};check(raw.bytes.byteLength===2&&new Uint8Array(raw.bytes)[1]===255,'raw download untouched');check(raw.sha==='a'.repeat(64),'header captured');check(calls[2].o.method==='POST'&&JSON.parse(calls[2].o.body).purpose===' original purpose ','download records explicit purpose')
 globalThis.fetch=async()=>new Response(new Uint8Array(MAX_FILE_BYTES+1));let capped=false;try{await intakeRequest('C','Investigator\n调查员 A','/evidence-intakes/d:download',new AbortController().signal,{purpose:'x'},true)}catch{capped=true}check(capped,'download budget fails closed')
 const readControl=new AbortController(), transport:any[]=[]
 globalThis.fetch=async(u,o)=>{transport.push({u,o});return new Response(JSON.stringify(preview))}
 await intakeRequest('C','Investigator\n调查员 A','/evidence-intakes:preview',readControl.signal,body)
 await intakeRequest('C','Investigator\n调查员 A','/evidence/EV-001/intake',readControl.signal)
 check(transport[0].o.signal===readControl.signal,'preview keeps abortable read signal');check(transport[1].o.signal===readControl.signal,'receipt keeps abortable read signal')
 let release:(value:Response)=>void=()=>{};globalThis.fetch=async(u,o)=>{transport.push({u,o});return new Promise<Response>(resolve=>{release=resolve})}
 const writeControl=new AbortController();const pending=intakeRequest('C','Investigator\n调查员 A','/evidence-intakes:commit',writeControl.signal,{...body,requestDigest:preview.requestDigest,confirmed:true})
 check(transport[2].o.signal===undefined,'commit detaches resettable read signal');check(transport[2].o.keepalive!==true,'large file does not use keepalive')
 writeControl.abort();release(new Response(JSON.stringify(receipt)));check((await pending as typeof receipt).evidenceId==='EV-001','dispatched commit transport completes after UI read abort')
 const alreadyAborted=new AbortController();alreadyAborted.abort();let stopped=false;try{await intakeRequest('C','Investigator\n调查员 A','/evidence-intakes:commit',alreadyAborted.signal,body)}catch{stopped=true}check(stopped&&transport.length===3,'pre-dispatch cancelled intent does not send')
 globalThis.fetch=async(u,o)=>{transport.push({u,o});return new Response(new Uint8Array(),{headers:{'X-Sha256':'b'.repeat(64)}})}
 await intakeRequest('C','Investigator\n调查员 A','/evidence-intakes/d:download',readControl.signal,{purpose:'x'},true);check(transport[3].o.signal===readControl.signal,'download retains existing abort semantics')
 console.log(`W4.2 ${n} model/API/render assertions passed`)
}
main().catch(e=>{console.error(e);process.exitCode=1})

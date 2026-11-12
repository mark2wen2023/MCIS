import { renderToStaticMarkup } from 'react-dom/server'
import { importBody,parsePreview,parseReceipt,encodeBytes,TEMPLATE,MAX_FILE_BYTES } from '../src/trackInput/model'
let n=0;const check=(v:unknown,s:string)=>{if(!v)throw Error(s);n++}
const reject=(fn:()=>unknown)=>{let yes=false;try{fn()}catch{yes=true}check(yes,'invalid input rejected')}
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
const body=importBody('V1','original.csv',' source ',' full UTC ','YWJj')
check(body.source==='source'&&body.timeBasis==='full UTC','trimmed user declarations only')
for(const args of [['','a.csv','s','t','YQ=='],['v','','s','t','YQ=='],['v','a.csv','','t','YQ=='],['v','a.csv','s','','YQ=='],['v','a.csv','s','t',''],['v','a.csv','s'.repeat(1001),'t','YQ==']])reject(()=>importBody(...args as [string,string,string,string,string]))
check(encodeBytes(new Uint8Array([0,255,13,10,239,187,191]))==='AP8NCu+7vw==','raw bytes BOM newline preserved')
check(TEMPLATE.split('\n').length===2&&!TEMPLATE.includes('2026'),'empty template no fake fixture')
check(MAX_FILE_BYTES===1048576,'file cap explicit')
const point={vesselId:'V1',timeSec:0,utc:'2026-01-01T00:00:00Z',latDeg:0,lonDeg:0,sogKn:102.2,cogDeg:0,hdgDeg:null}
const p={profile:'mcis-utc-v1',caseId:'A',vesselId:'V1',caseEpochUtc:point.utc,previewDigest:'a'.repeat(64),sourceSha256:'b'.repeat(64),rowCount:1,canCommit:true,issues:[],issuesTotal:0,issuesTruncated:false,samplePoints:[point],warnings:[],existingTrackCount:0,fileName:body.fileName,source:body.source,timeBasis:body.timeBasis,timeRange:{firstUtc:point.utc,lastUtc:point.utc,fromSec:0,toSec:0}}
check(parsePreview(p,'A',body).samplePoints[0]!.sogKn===102.2,'reported 102.2 not inferred saturated')
for(const delta of [{caseId:'B'},{vesselId:'V2'},{source:'changed'},{fileName:'changed.csv'},{rowCount:-1},{rowCount:10001},{rowCount:0},{issuesTotal:1},{existingTrackCount:1},{previewDigest:'bad'},{sourceSha256:'bad'},{warnings:[{}]},{samplePoints:[{...point,sogKn:NaN}]},{samplePoints:[{...point,vesselId:'V2'}]},{samplePoints:Array(101).fill(point)},{timeRange:undefined}])reject(()=>parsePreview({...p,...delta},'A',body))
check(parsePreview({...p,canCommit:false,rowCount:1,issuesTotal:1,issues:[{row:2,field:'sogStatus',code:'LOWER_BOUND',message:'Only lower bound'}],samplePoints:[],timeRange:null},'A',body).canCommit===false,'blocked file preview permitted')
const r={caseId:'A',vesselId:'V1',previewDigest:p.previewDigest,sourceSha256:p.sourceSha256,pointCount:1,sourceEvidenceId:'EV-1',reportEvidenceId:'EV-2',committedUtc:point.utc,replayed:false}
check(parseReceipt(r,'A','V1',p).pointCount===1,'receipt verified')
for(const delta of [{caseId:'B'},{vesselId:'V2'},{previewDigest:'c'.repeat(64)},{sourceSha256:'c'.repeat(64)},{pointCount:0},{pointCount:2},{sourceEvidenceId:''},{reportEvidenceId:null},{replayed:'false'},{reportSha256:'bad'}])reject(()=>parseReceipt({...r,...delta},'A','V1',p))
async function main(){const {TrackInputPanel}=await import('../src/trackInput/TrackInputPanel');const html=renderToStaticMarkup(<TrackInputPanel who={'Investigator\n调查员 A'} snapshot={{case:{caseId:'A',title:'Synthetic',isFictionalDemo:true,caseEpochUtc:point.utc},vessels:[],tracks:[]}}/>);check(html.includes('导入明确语义 UTC CSV'),'closed honest entry');check(!html.includes('已保存'),'no false saved state')
const {importRequest}=await import('../src/trackInput/api');const calls:any[]=[];globalThis.fetch=async(u,o)=>{calls.push({u,o});return new Response(JSON.stringify(p))};await importRequest('A','Investigator\n调查员 A',':preview',new AbortController().signal,body);check(calls.length===1&&calls[0].o.method==='POST','explicit post only after called');check(calls[0].u==='/api/v1/cases/A/track-imports:preview','case scoped');check(JSON.parse(calls[0].o.body).contentBase64===body.contentBase64,'original bytes encoded not reparsed');let denied=false;try{await importRequest('A','other',':commit',new AbortController().signal,body)}catch{denied=true}check(denied&&calls.length===1,'identity rejects stale request');console.log(`W10.2 ${n} assertions passed`)}
main().catch(e=>{console.error(e);process.exitCode=1})

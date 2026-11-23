import React from 'react'
import {allowedRequest} from './request-policy.mjs'
import {getInstanceByDom} from 'echarts'
const conflictMode = new URLSearchParams(location.search).has('conflicts')
import {createRoot} from 'react-dom/client'
import {MemoryRouter, useNavigate} from 'react-router-dom'
import '../../src/styles.css'

localStorage.clear()
localStorage.setItem('mcis.role','Investigator')
localStorage.setItem('mcis.operator','SYNTHETIC-ONE')
type Pending = {id:number; url:string; operator:string; finish:(value:Response)=>void}
const pending:Pending[]=[]
let serial=0
const unexpected:string[]=[]
window.fetch=(input,init)=>new Promise<Response>(resolve=>{
 const url=String(input)
 if(!allowedRequest(url,init?.method??'GET')) {
  unexpected.push('unexpected request'); resolve(new Response('{}',{status:403})); return
 }
 if(conflictMode && url.endsWith('/conflicts')) {pending.push({id:++serial,url,operator:String((init?.headers as Record<string,string>)?.['X-MCIS-Operator']),finish:resolve});return}
 if(conflictMode && url === '/api/v1/cases/SYN-A') {resolve(Response.json({caseId:'SYN-A',title:'Synthetic conflict case',caseEpochUtc:'2026-01-01T00:00:00Z',displayTimeZoneOffsetMinutes:0,isFictionalDemo:true}));return}
 if(conflictMode && url.endsWith('/timeline')) {resolve(Response.json({caseEpochUtc:'2026-01-01T00:00:00Z',durationSec:60,events:[{eventId:'SYN-EVENT',kind:'Event',timeSec:10,title:'AVAILABLE-EVENT',presumptive:true,sourceLabel:'synthetic'}]}));return}
 if(conflictMode && url.endsWith('/tracks')) {resolve(Response.json({tracks:[]}));return}
 if(url.endsWith('/evidence'))pending.push({id:++serial,url,operator:String((init?.headers as Record<string,string>)?.['X-MCIS-Operator']),finish:resolve})
 else resolve(new Response(JSON.stringify({code:'UNAVAILABLE',message:'Synthetic ancillary unavailable'}),{status:403}))
})
const {EvidencePage}=await import('../../src/pages/EvidencePage')
const {setIdentity}=await import('../../src/api')
function Fixture(){const navigate=useNavigate();return <><p>合成请求测试；非业务服务、非真实登录。</p><button onClick={()=>navigate('/evidence?case=SYN-A')}>Case A</button><button onClick={()=>navigate('/evidence?case=SYN-B')}>Case B</button><button onClick={()=>setIdentity('Public','SYNTHETIC-TWO')}>Synthetic identity change</button><EvidencePage/></>}
const gate={
 chart:()=>{
  const el=document.querySelector<HTMLElement>('.w4-page [_echarts_instance_]')
  return el ? getInstanceByDom(el)?.getOption() : null
 },
 settleConflict:(id:number,kind:'deny'|'empty'|'data')=>{
  const i=pending.findIndex(p=>p.id===id && p.url==='/api/v1/cases/SYN-A/conflicts');if(i<0)throw Error('unknown conflict request')
  const [p]=pending.splice(i,1)
  const row={conflictId:'SYN-UNKNOWN',summary:'UNKNOWN-TIME-CONFLICT',trackKind:'synthetic',timeSec:null,a:{sourceLabel:'synthetic A',valueText:'A'},b:{sourceLabel:'synthetic B',valueText:'B'},deltaUnit:'s',status:'Open',resolution:'',detectedBy:'fixture'}
  p.finish(Response.json(kind==='deny'?{code:'FORBIDDEN',message:'CONFLICT-DENIED'}:kind==='empty'?[]:[row,{...row,conflictId:'SYN-ZERO',summary:'ZERO-TIME-CONFLICT',timeSec:0,status:'Resolved'}],{status:kind==='deny'?403:200}))
 },
 latestId:()=>serial,
 requests:()=>pending.map(({id,url,operator})=>({id,url,operator})),
 unexpected:()=>unexpected,
 settle:(id:number,kind:'data'|'empty'|'deny',title:string)=>{const i=pending.findIndex(p=>p.id===id);if(i<0)throw Error('unknown request');const [p]=pending.splice(i,1);const caseId=p.url.includes('SYN-A')?'SYN-A':'SYN-B';const item={caseId,evidenceId:'EV-001',title,source:'synthetic',extractedBy:'synthetic',extractedUtc:'2026-01-01T00:00:00Z',sha256:'a'.repeat(64),currentSha256:'a'.repeat(64),confidentiality:'Normal',status:'Unverified',needsReview:false,accessCount:0};p.finish(new Response(JSON.stringify(kind==='deny'?{code:'FORBIDDEN',message:title||'CURRENT-DENIAL'}:kind==='empty'?[]:[item]),{status:kind==='deny'?403:200}))}
}
;(window as unknown as {gate:typeof gate}).gate=gate
createRoot(document.getElementById('root')!).render(<MemoryRouter initialEntries={['/evidence?case=SYN-A']}><Fixture/></MemoryRouter>)

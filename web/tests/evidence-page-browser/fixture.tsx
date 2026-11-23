import React from 'react'
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
 if((init?.method??'GET')!=='GET'||!/^\/api\/v1\/cases\/SYN-[AB](?:\/|$)/.test(url)) {
  unexpected.push('unexpected request'); resolve(new Response('{}',{status:403})); return
 }
 if(url.endsWith('/evidence'))pending.push({id:++serial,url,operator:String((init?.headers as Record<string,string>)?.['X-MCIS-Operator']),finish:resolve})
 else resolve(new Response(JSON.stringify({code:'UNAVAILABLE',message:'Synthetic ancillary unavailable'}),{status:403}))
})
const {EvidencePage}=await import('../../src/pages/EvidencePage')
const {setIdentity}=await import('../../src/api')
function Fixture(){const navigate=useNavigate();return <><p>合成请求测试；非业务服务、非真实登录。</p><button onClick={()=>navigate('/evidence?case=SYN-A')}>Case A</button><button onClick={()=>navigate('/evidence?case=SYN-B')}>Case B</button><button onClick={()=>setIdentity('Public','SYNTHETIC-TWO')}>Synthetic identity change</button><EvidencePage/></>}
const gate={
 requests:()=>pending.map(({id,url,operator})=>({id,url,operator})),
 unexpected:()=>unexpected,
 settle:(id:number,kind:'data'|'empty'|'deny',title:string)=>{const i=pending.findIndex(p=>p.id===id);if(i<0)throw Error('unknown request');const [p]=pending.splice(i,1);const caseId=p.url.includes('SYN-A')?'SYN-A':'SYN-B';const item={caseId,evidenceId:'EV-001',title,source:'synthetic',extractedBy:'synthetic',extractedUtc:'2026-01-01T00:00:00Z',sha256:'a'.repeat(64),currentSha256:'a'.repeat(64),confidentiality:'Normal',status:'Unverified',needsReview:false,accessCount:0};p.finish(new Response(JSON.stringify(kind==='deny'?{code:'FORBIDDEN',message:'Synthetic denied'}:kind==='empty'?[]:[item]),{status:kind==='deny'?403:200}))}
}
;(window as unknown as {gate:typeof gate}).gate=gate
createRoot(document.getElementById('root')!).render(<MemoryRouter initialEntries={['/evidence?case=SYN-A']}><Fixture/></MemoryRouter>)

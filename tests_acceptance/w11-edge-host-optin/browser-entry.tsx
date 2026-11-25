import {useEffect,useState} from 'react'
import {createRoot} from 'react-dom/client'
import {EdgeSelection,type CandidateEdgeReader} from './src/ecfcDrafts/EdgeSelection'
import {parseEnvelope,type Document} from './src/ecfcDrafts/model'

const caseId='SYN-XREPO-001'
const prefix='/__local_synthetic_w11/'+caseId
const headers={'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'LocalSyntheticLead'}
const reader:CandidateEdgeReader=async context=>{
 const r=await fetch(prefix+'/edge-excerpt',{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify(context),cache:'no-store'})
 if(!r.ok)throw Error('Unavailable')
 return r.json()
}
function App(){
 const [doc,setDoc]=useState<Document|null>(null),[bad,setBad]=useState(false)
 useEffect(()=>{
  let current=true
  void fetch(prefix+'/draft',{headers,cache:'no-store'})
   .then(async r=>{if(!r.ok)throw Error();return parseEnvelope(await r.json(),caseId)})
   .then(e=>{if(current&&e.sourceStatus==='unchanged')setDoc(e.document);else if(current)setBad(true)})
   .catch(()=>{if(current)setBad(true)})
  return()=>{current=false}
 },[])
 return <main><h1>W11 单边原件读取合成验收</h1>{doc?<EdgeSelection draft={doc.draft} validation={doc.validation} document={doc} reader={reader}/>:<p>{bad?'来源不可用':'读取当前保存草稿…'}</p>}</main>
}
createRoot(document.getElementById('root')!).render(<App/>)

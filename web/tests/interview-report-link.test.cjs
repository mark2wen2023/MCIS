// Actual page selection with synthetic hooks/roster; no browser or API calls.
const assert=require('node:assert/strict')
const vm=require('node:vm')
const {buildSync}=require('esbuild')
const code=buildSync({entryPoints:['src/pages/InterviewPage.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
function selection(query){
 const params=new URLSearchParams(query),caseId=params.get('case')||'SYNTHETIC-DEMO'
 const jsx=(type,props)=>({type,props})
 const noop=()=>null
 const modules={
  react:{useState:v=>[typeof v==='function'?v():v,()=>{}],useSyncExternalStore:(_s,get)=>get(),useEffect:()=>{},useRef:v=>({current:v})},
  'react/jsx-runtime':{jsx,jsxs:jsx,Fragment:'fragment'},
  'react-router-dom':{useSearchParams:()=>[params,()=>{}]},
  '../api':{CASE_ID:'SYNTHETIC-DEMO',getRole:()=> 'Investigator',getOperator:()=> 'Synthetic',onIdentityChange:()=>{},ApiError:class extends Error{},casePath:()=>{throw Error('no API paths expected')}},
  '../components/Toast':{useToast:()=>{throw Error('no actions expected')}},
  '../interview/contentAccess':{CONTENT_ACCESS_NOTICE:'synthetic',contentIdentity:()=> 'synthetic',useContentLoad:()=>({data:{caseId,records:[{recordId:'IR-001'},{recordId:'IR-002'},{recordId:'IR-03'}]},reload:()=>{}})},
  '../interview/InterviewView':{InterviewView:noop},'../interview/labels':{},'../interview/interview.css':{},
  '../interviewIntake/Panel':{ManualInterviewPanel:noop},'../archiveProvenance/Provenance':{ArchiveProvenance:noop},'../agents/AgentReviewPanel':{AgentReviewPanel:noop}
 }
 const box={exports:{}}
 vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}})
 const page=box.exports.InterviewPage(),casePage=page.type(page.props)
 const allowed=casePage.props.children.find(n=>typeof n?.type==='function')
 const rendered=allowed.type(allowed.props)
 const record=rendered.props.children.find(n=>n.type.name==='InterviewRecordPage')
 return {caseId:record.props.caseId,current:record.props.current}
}
const cases=[
 ['case=SYNTHETIC-B&id=IR-002&statement=S-7','SYNTHETIC-B','IR-002'],
 ['case=SYNTHETIC-B&record=IR-002','SYNTHETIC-B','IR-002'],
 ['case=SYNTHETIC-B&record=IR-001&id=IR-002','SYNTHETIC-B','IR-001'],
 ['case=SYNTHETIC-B&id=IR-MISSING','SYNTHETIC-B','IR-MISSING'],
 ['case=SYNTHETIC-B','SYNTHETIC-B','IR-001'],
 ['', 'SYNTHETIC-DEMO','IR-03']
]
for(const [query,caseId,current] of cases)assert.deepEqual(selection(query),{caseId,current},query)
console.log('interview report link: 6 synthetic actual-page selection scenarios passed')

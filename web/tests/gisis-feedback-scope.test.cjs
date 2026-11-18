// Actual ReportSession callbacks; synthetic hooks, deferred API and no startup effects.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),{buildSync}=require('esbuild')
const source=fs.readFileSync('src/pages/ReportPage.tsx','utf8')+'\nexport { ReportSession };'
const code=buildSync({stdin:{contents:source,sourcefile:'ReportPage.tsx',loader:'tsx'},bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const jsx=(type,props,key)=>({type,props,key}),View=()=>null
const nodes=n=>!n?[]:Array.isArray(n)?n.flatMap(nodes):typeof n==='object'?[n,...nodes(n.props?.children)]:[]
async function scenario(mode){
 let index=0;const state=[],requests=[]
 const api={glossary:async()=>({}),gisisValidate:(c,v)=>new Promise((resolve,reject)=>requests.push({c,v,resolve,reject})),gisisValidateExport:(c,v)=>new Promise((resolve,reject)=>requests.push({c,v,resolve,reject}))}
 const modules={react:{useState:v=>{const i=index++;if(!(i in state))state[i]=v;return[state[i],v=>state[i]=typeof v==='function'?v(state[i]):v]},useRef:v=>{const i=index++;if(!(i in state))state[i]={current:v};return state[i]},useMemo:f=>f(),useEffect:()=>{},useLayoutEffect:()=>{}},'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[new URLSearchParams('case=SYNTHETIC'),()=>{}]},'../reports/api':{createReportApi:()=>api,ReportApiError:class extends Error{}},'../reports/ReportView':{ReportView:View,ReviewDialog:()=>null},'../api':{getRole:()=> 'synthetic',getOperator:()=> 'synthetic',onIdentityChange:()=>()=>{}},'../cases/model':{parseCases:v=>v},'../reportOutput/Panel':{ReportOutputPanel:()=>null},'../archiveProvenance/Provenance':{ArchiveProvenance:()=>null},'../reports/types':{DEMO_CASE_ID:'SYNTHETIC'}}
 const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}})
 const render=()=>{index=0;return nodes(box.exports.ReportSession({identity:'["synthetic","synthetic"]',isActive:()=>true,refresh:()=>{}})).find(n=>n.type===View).props}
 if(mode==='glossary'){
  render().onGlossary();await new Promise(setImmediate)
  const message=render().notice;assert.match(message,/已下载 IMO/)
  render().onGisisEdit()
  assert.equal(render().notice,message,'editing GISIS must retain unrelated completed-operation notice')
 } else {
  render().onGisisValidate({field:'A'},false)
  if(mode==='stale')render().onGisisEdit()
  requests[0].reject(new Error('synthetic old field error'));await new Promise(setImmediate)
  if(mode==='stale'){
   assert.ok(!render().error?.includes('synthetic old field error'),'old error must not describe current input')
   assert.match(render().notice,/输入已变化/)
   assert.equal(render().validation,null)
  } else {
   assert.match(render().error,/synthetic old field error/)
   render().onGisisEdit()
   assert.ok(!render().error?.includes('synthetic old field error'),'editing invalidates prior GISIS error only')
  }
  assert.equal(requests.length,1)
 }
}
;(async()=>{for(const mode of (process.argv[2]?[process.argv[2]]:['stale','current','glossary']))await scenario(mode);console.log('GISIS feedback scope: 3 synthetic callback flows passed')})().catch(e=>{console.error(e);process.exitCode=1})

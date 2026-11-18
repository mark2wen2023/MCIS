// Actual Layout function, synthetic hooks/router/API; no browser or HTTP.
const assert = require('node:assert/strict')
const vm = require('node:vm')
const { buildSync } = require('esbuild')
const code = buildSync({entryPoints:['src/Layout.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const values=[], effects=[], queued=[], requests=[]
let cursor=0, effectCursor=0, caseId='SYNTHETIC-A'
const Status=()=>null
const jsx=(type,props)=>({type,props})
const api={get:()=>new Promise((resolve,reject)=>requests.push({resolve,reject}))}
const modules={
  react:{useState:initial=>{const i=cursor++;if(!(i in values))values[i]=initial;return[values[i],v=>values[i]=typeof v==='function'?v(values[i]):v]},
    useEffect:(fn,deps)=>{const i=effectCursor++;const previous=effects[i];if(!previous||deps.some((d,j)=>d!==previous.deps[j]))queued.push(()=>{previous?.cleanup?.();effects[i]={deps,cleanup:fn()}})}},
  'react/jsx-runtime':{jsx,jsxs:jsx},
  'react-router-dom':{NavLink:'nav',Outlet:'outlet',useLocation:()=>({pathname:'/evidence'}),useSearchParams:()=>[new URLSearchParams({case:caseId})]},
  './api':{api,CASE_ID:'SYNTHETIC-FALLBACK',getRole:()=> 'Investigator',getOperator:()=> 'Synthetic',setIdentity:()=>{}},
  './caseMetadata/events':{onCaseMetadataChanged:()=>()=>{}},
  './routes':{ROUTES:[]},'./config':{SERVICE_ADDR:'synthetic-no-server'},
  './caseContext':{caseForLocation:(_p,s)=>new URLSearchParams(s).get('case'),navigationForCase:()=>''},
  './components/CaseLoadStatus':{CaseLoadStatus:Status},
}
const moduleBox={exports:{}}
vm.runInNewContext(code,{module:moduleBox,exports:moduleBox.exports,URLSearchParams,require:name=>{assert.ok(name in modules,name);return modules[name]}})
function render(){cursor=0;effectCursor=0;return moduleBox.exports.Layout()}
function find(node){if(!node)return null;if(Array.isArray(node))return node.map(find).find(Boolean);if(node.type===Status)return node;return find(node.props?.children)}
function flush(){while(queued.length)queued.shift()()}
async function settle(){await Promise.resolve();await Promise.resolve();await Promise.resolve()}
;(async()=>{
  render();flush();requests[0].reject(Error('synthetic case unavailable'));await settle()
  assert.equal(find(render()).props.loaded,false)
  caseId='SYNTHETIC-B'
  assert.equal(find(render()).props.loaded,null,'B must not show A failure before effects')
  flush();requests[1].resolve({caseId,title:'synthetic B',isFictionalDemo:true});await settle()
  assert.equal(find(render()).props.loaded,true)
  caseId='SYNTHETIC-C'
  assert.equal(find(render()).props.loaded,null,'C must not show B success before effects')
  flush()
  caseId='SYNTHETIC-D';render();flush()
  requests[2].reject(Error('late synthetic C error'));await settle()
  assert.equal(find(render()).props.loaded,null,'late C failure must not replace D loading')
  requests[3].resolve({caseId,title:'synthetic D',isFictionalDemo:true});await settle()
  assert.equal(find(render()).props.loaded,true)
  console.log('Layout transitions: 6 synthetic lifecycle assertions passed')
})().catch(e=>{console.error(e);process.exitCode=1})

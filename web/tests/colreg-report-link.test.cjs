// Actual page, synthetic hook/router/load results. No HTTP, core or mutations.
const assert=require('node:assert/strict')
const vm=require('node:vm')
const {buildSync}=require('esbuild')
const code=buildSync({entryPoints:['src/pages/ColregPage.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
function render(query,mode='ready'){
 const params=new URLSearchParams(query),caseId=params.get('case')||'SYNTHETIC-DEMO',paths=[]
 const View=()=>null,jsx=(type,props,key)=>({type,props,key})
 const analysis={caseId,bands:[],checks:[{checkId:'CK-1'},{checkId:'CK-2'}]}
 const get=path=>{
  paths.push(path)
  if(path==='/cases')return []
  if(path.endsWith('/colreg/runs'))return {runs:[],activeRunId:'RUN-NEW'}
  if(path.includes('/colreg/runs/'))return mode==='loading'?null:mode==='error'?{syntheticError:true}: {runId:mode==='mismatch'?'RUN-WRONG':path.endsWith('/active')?'RUN-NEW':decodeURIComponent(path.split('/').at(-1)),analysis,annotations:{}}
  if(path.endsWith('/colreg'))return analysis
  if(path.endsWith('/'+caseId))return {caseId,title:'synthetic case'}
  return []
 }
 const modules={react:{useState:v=>[typeof v==='function'?v():v,()=>{}],useMemo:f=>f()},
 'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[params,()=>{}]},
 '../api':{api:{get},ApiError:class extends Error{},CASE_ID:'SYNTHETIC-DEMO'},
 '../colreg/ColregView':{ColregView:View},'../colreg/derive':{},
 '../components/Toast':{useToast:()=>({run:()=>{throw Error('no mutations')},show:()=>{}})},
 '../hooks':{useLoad:f=>{const data=f();return {data:data?.syntheticError?null:data,error:data?.syntheticError?'synthetic unavailable':null,reload:()=>{}}}},'../styles/w6.css':{}}
 const box={exports:{}}
 vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}})
 let node=box.exports.ColregPage();let sessionKey=node.key
 while(typeof node.type==='function'&&node.type!==View){node=node.type(node.props);sessionKey+=':'+node.key}
 function find(n){if(!n)return null;if(Array.isArray(n))return n.map(find).find(Boolean);if(n.type===View)return n;return find(n.props?.children)}
 return {node:find(node)||node,paths,View,sessionKey}
}
const historical=render('case=SYNTHETIC-B&check=CK-2&run=RUN-OLD')
assert.equal(historical.node.props.selectedId,'CK-2','report check must not silently select first item')
assert.equal(historical.node.props.runView.runId,'RUN-OLD','report run must not silently select active run')
assert.ok(historical.paths.includes('/cases/SYNTHETIC-B/colreg/runs/RUN-OLD'))
for(const mode of ['loading','error','mismatch']){
 const r=render('case=SYNTHETIC-B&check=CK-2&run=RUN-OLD',mode)
 assert.notEqual(r.node.type,r.View,mode+' must not display current fallback')
}
const missing=render('case=SYNTHETIC-B&check=CK-MISSING&run=RUN-OLD')
assert.notEqual(missing.node.type,missing.View,'missing check must not display another check')
const legacy=render('case=SYNTHETIC-B&check=CK-2')
assert.equal(legacy.node.props.selectedId,'CK-2')
const ordinary=render('case=SYNTHETIC-B')
assert.equal(ordinary.node.props.selectedId,'CK-1')
assert.equal(ordinary.node.props.runView.runId,'RUN-NEW')
assert.notEqual(historical.sessionKey,render('case=SYNTHETIC-B&check=CK-1&run=RUN-OLD').sessionKey)
assert.notEqual(historical.sessionKey,render('case=SYNTHETIC-C&check=CK-2&run=RUN-OLD').sessionKey)
console.log('COLREG link: 9 synthetic page scenarios / 12 assertions passed')

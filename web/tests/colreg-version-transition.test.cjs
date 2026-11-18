// Actual page + useLoad; synthetic React lifecycle/router/deferred API, no HTTP.
const assert=require('node:assert/strict'),vm=require('node:vm'),{buildSync}=require('esbuild')
const code=buildSync({entryPoints:['src/pages/ColregPage.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',write:false,external:['react','react/jsx-runtime','react-router-dom','../api','./api','../colreg/*','../components/*','../styles/*']}).outputFiles[0].text
const View=()=>null,jsx=(type,props,key)=>({type,props,key})
let params=new URLSearchParams('case=SYNTHETIC&run=RUN-A'),values=[],effects=[],queued=[],index=0,ei=0,lastKey
const frames=new Map()
const requests=[]
const analysis={caseId:'SYNTHETIC',checks:[{checkId:'CK-1'}],bands:[]}
const api={get:path=>new Promise(resolve=>requests.push({path,resolve}))}
const apiModule={api,CASE_ID:'DEMO',ApiError:class extends Error{},onIdentityChange:()=>()=>{}}
const modules={react:{useRef:v=>{const store=values,n=index++;if(!(n in store))store[n]={current:v};return store[n]},useState:v=>{const store=values,i=index++;if(!(i in store))store[i]=typeof v==='function'?v():v;return[store[i],v=>store[i]=typeof v==='function'?v(store[i]):v]},useMemo:f=>f(),useCallback:f=>f,
useEffect:(fn,deps)=>{const store=effects,i=ei++,old=store[i];if(!old||deps.some((d,j)=>d!==old.deps[j]))queued.push(()=>{old?.cleanup?.();store[i]={deps,cleanup:fn()}})}},
'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[params,q=>{params=new URLSearchParams(q)}]},'../api':apiModule,'./api':apiModule,'../colreg/ColregView':{ColregView:View},'../colreg/derive':{},'../components/Toast':{useToast:()=>({show:()=>{},run:()=>{throw Error('no writes')}})},'../styles/w6.css':{}}
const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}})
function find(n){if(!n)return null;if(Array.isArray(n))return n.map(find).find(Boolean);if(n.type===View)return n;return find(n.props?.children)}
function render(){
 let node={type:box.exports.ColregPage,props:{},key:'root'},path=''
 const active=new Set()
 while(typeof node.type==='function'&&node.type!==View){
  path+='/'+node.type.name+':'+node.key;active.add(path)
  let frame=frames.get(path);if(!frame){frame={values:[],effects:[]};frames.set(path,frame)}
  values=frame.values;effects=frame.effects;index=0;ei=0;node=node.type(node.props)
 }
 for(const [key,frame] of frames)if(!active.has(key)){frame.effects.forEach(e=>e?.cleanup?.());frames.delete(key)}
 return {tree:node,view:find(node)}
}
function flush(){while(queued.length)queued.shift()()}
async function complete(){for(const r of requests.splice(0)){let data=[];if(r.path.includes('/colreg/runs/'))data={runId:r.path.endsWith('/active')?'RUN-CURRENT':r.path.split('/').at(-1),analysis};else if(r.path.endsWith('/colreg'))data=analysis;else if(r.path.endsWith('/SYNTHETIC'))data={caseId:'SYNTHETIC',title:'synthetic'};else if(r.path.endsWith('/colreg/runs'))data={runs:[],activeRunId:'RUN-CURRENT'};r.resolve(data)}await Promise.resolve();await Promise.resolve()}
;(async()=>{
 render();flush();await complete();const first=render();assert.equal(first.view.props.runView.runId,'RUN-A')
 first.view.props.onViewRun('RUN-B')
 const waiting=render()
 assert.ok(!JSON.stringify(waiting.tree).includes('返回版本不符'),'waiting B must not judge stale A as mismatched B')
 assert.ok(!waiting.view,'must not display stale A while B pending')
 flush();await complete();assert.equal(render().view.props.runView.runId,'RUN-B')
 params=new URLSearchParams('case=SYNTHETIC&run=active');render();flush();await complete()
 assert.equal(render().view?.props.runView.runId,'RUN-CURRENT','active is endpoint alias, not literal stored runId')
 console.log('COLREG transition: 5 synthetic lifecycle assertions passed')
})().catch(e=>{console.error(e);process.exitCode=1})

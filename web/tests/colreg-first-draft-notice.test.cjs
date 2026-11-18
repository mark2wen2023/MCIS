// Actual page + useLoad; synthetic React lifecycle/router/deferred API, no HTTP.
const assert=require('node:assert/strict'),vm=require('node:vm'),{buildSync}=require('esbuild')
const code=buildSync({entryPoints:['src/pages/ColregPage.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',write:false,external:['react','react/jsx-runtime','react-router-dom','../api','./api','../colreg/*','../components/*','../styles/*']}).outputFiles[0].text
const View=()=>null,jsx=(type,props,key)=>({type,props,key})
let params=new URLSearchParams('case=SYNTHETIC&run=RUN-A'),values=[],effects=[],queued=[],index=0,ei=0,lastKey
const frames=new Map()
const requests=[]
const notices=[]
const analysis={caseId:'SYNTHETIC',checks:[{checkId:'CK-1'}],bands:[]}
const api={get:path=>new Promise((resolve,reject)=>requests.push({path,resolve,reject})),post:async()=>({title:'synthetic draft',text:'keep this draft',status:'Draft'})}
const apiModule={api,CASE_ID:'DEMO',ApiError:class extends Error{},onIdentityChange:()=>()=>{}}
const modules={react:{useRef:v=>{const store=values,n=index++;if(!(n in store))store[n]={current:v};return store[n]},useState:v=>{const store=values,i=index++;if(!(i in store))store[i]=typeof v==='function'?v():v;return[store[i],v=>store[i]=typeof v==='function'?v(store[i]):v]},useMemo:f=>f(),useCallback:f=>f,
useEffect:(fn,deps)=>{const store=effects,i=ei++,old=store[i];if(!old||deps.some((d,j)=>d!==old.deps[j]))queued.push(()=>{old?.cleanup?.();store[i]={deps,cleanup:fn()}})}},
'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[params,q=>{params=new URLSearchParams(q)}]},'../api':apiModule,'./api':apiModule,'../colreg/ColregView':{ColregView:View},'../colreg/derive':{normalizeDraftResponse:v=>v},'../components/Toast':{useToast:()=>({show:(...args)=>notices.push(args),run:async f=>f()})},'../styles/w6.css':{}}
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
async function complete(){for(const r of requests.splice(0)){let data=[];if(r.path.includes('/colreg/runs/'))data={runId:r.path.endsWith('/active')?'RUN-CURRENT':r.path.split('/').at(-1),analysis:{...analysis,caseId:r.path.split('/')[2]}};else if(r.path.endsWith('/colreg'))data=analysis;else if(r.path.endsWith('/SYNTHETIC')||r.path.endsWith('/SYNTHETIC-OTHER'))data={caseId:r.path.split('/')[2],title:'synthetic'};else if(r.path.endsWith('/colreg/runs'))data={runs:[],activeRunId:'RUN-CURRENT'};r.resolve(data)}await Promise.resolve();await Promise.resolve()}
;(async()=>{
 render();flush();await complete();render()
 const posts=[];api.post=()=>new Promise(resolve=>posts.push(resolve))
 const first=render().view;first.props.onGenerateDraft()
 first.props.onViewRun('RUN-B')
 const message='不代表服务未生成报告'
 assert.ok(JSON.stringify(render().tree).includes(message),'first outstanding draft must have guidance while new version loads')
 flush();await complete()
 assert.ok(JSON.stringify(render().tree).includes(message),'guidance must remain without a prior draft/result')
 assert.equal(render().view.props.draft,null)
 posts.shift()({text:'late initial draft',status:'Draft'});await new Promise(setImmediate)
 assert.equal(render().view.props.draft,null,'late initial result still suppressed')
 params=new URLSearchParams('case=SYNTHETIC&run=RUN-C');render();flush()
 for(const r of requests.splice(0))r.resolve(r.path.includes('/colreg/runs/RUN-C')?{runId:'WRONG',analysis}:r.path.endsWith('/SYNTHETIC')?{caseId:'SYNTHETIC'}:[])
 await new Promise(setImmediate)
 assert.ok(JSON.stringify(render().tree).includes(message),'unavailable target must retain guidance')
 console.log('COLREG first draft: 5 synthetic lifecycle assertions passed')
})().catch(e=>{console.error(e);process.exitCode=1})

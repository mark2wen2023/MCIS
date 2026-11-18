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
 const posts=[];api.post=()=>new Promise((resolve,reject)=>posts.push({resolve,reject}))
 render().view.props.onGenerateDraft();posts.shift().resolve({text:'existing draft',status:'Draft'});await new Promise(setImmediate)
 const oldView=render().view
 oldView.props.onGenerateDraft()
 oldView.props.onCompare('RUN-A','RUN-C')
 const oldCompare=requests.pop()
 oldView.props.onViewRun('RUN-B');render();flush();await complete();render()
 posts.shift().resolve({text:'late A draft',status:'Draft'});oldCompare.resolve({baseRunId:'RUN-A',otherRunId:'RUN-C'});await new Promise(setImmediate)
 assert.equal(render().view.props.draft.text,'existing draft','late previous session must not replace retained draft')
 assert.equal(render().view.props.compare,null,'late previous session comparison must not publish')
 render().view.props.onGenerateDraft();render().view.props.onGenerateDraft()
 const older=posts.shift(),newer=posts.shift();newer.resolve({text:'newest draft',status:'Draft'});await new Promise(setImmediate)
 older.resolve({text:'out of order draft',status:'Draft'});await new Promise(setImmediate)
 assert.equal(render().view.props.draft.text,'newest draft')
 render().view.props.onCompare('RUN-B','RUN-C');render().view.props.onCompare('RUN-B','RUN-D')
 const second=requests.pop(),first=requests.pop();second.resolve({baseRunId:'RUN-B',otherRunId:'RUN-D'});await new Promise(setImmediate)
 first.resolve({baseRunId:'RUN-B',otherRunId:'RUN-C'});await new Promise(setImmediate)
 assert.equal(render().view.props.compare.otherRunId,'RUN-D')
 render().view.props.onGenerateDraft();render().view.props.onGenerateDraft()
 const errorOld=posts.shift(),successNew=posts.shift();successNew.resolve({text:'latest after old error',status:'Draft'});await new Promise(setImmediate)
 errorOld.reject(new Error('late error'));await new Promise(setImmediate)
 assert.equal(render().view.props.draftNotice,null)
 assert.equal(render().view.props.draft.text,'latest after old error')
 render().view.props.onCompare('RUN-B','RUN-C');const lateFailure=requests.pop()
 render().view.props.onViewRun('RUN-E');render();flush();await complete();render()
 const noticeCount=notices.length;lateFailure.reject(new Error('stale comparison error'));await new Promise(setImmediate)
 assert.equal(notices.length,noticeCount,'stale error must not replace current feedback')
 assert.equal(render().view.props.compare.otherRunId,'RUN-D','keep previous comparison on stale failure')
 console.log('COLREG async work: 8 synthetic delayed/ordered response assertions passed')
})().catch(e=>{console.error(e);process.exitCode=1})

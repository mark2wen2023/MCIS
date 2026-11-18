// Actual Detail and actual useScopedActions.run; synthetic hooks/promises. No HTTP/browser.
const assert=require('node:assert/strict'),vm=require('node:vm'),{buildSync}=require('esbuild')
const bundle=p=>buildSync({entryPoints:[p],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const pageCode=bundle('src/pages/RecommendationsPage.tsx'),toastCode=bundle('src/components/Toast.tsx')
const jsx=(type,props,key)=>({type,props,key})
function evaluate(code,modules){const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}});return box.exports}
function nodes(n){if(!n)return[];if(Array.isArray(n))return n.flatMap(nodes);return typeof n==='object'?[n,...nodes(n.props?.children)]:[]}
async function scenario(change,failure=false,reply=false){
 let values=[],index=0,loadIndex=0,cleanups=[];const notices=[];let reloads=0,sent=0
 const react={useRef:v=>{const a=values,i=index++;if(!(i in a))a[i]={current:v};return a[i]},useState:v=>{const a=values,i=index++;if(!(i in a))a[i]=v;return[a[i],v=>a[i]=typeof v==='function'?v(a[i]):v]},useSyncExternalStore:(_,f)=>f(),createContext:()=>({}),useContext:()=>((...n)=>notices.push(n)),useCallback:f=>f,useLayoutEffect:f=>{const i=index++;if(!(i in values)){values[i]=true;const c=f();if(c)cleanups.push(c)}}}
 const toast=evaluate(toastCode,{react,'react/jsx-runtime':{jsx,jsxs:jsx},'../api':{ApiError:class extends Error{}}})
 const rec=id=>({id,status:'Responded',column:'InProgress',progressPct:0,addressee:'synthetic',causeNodeIds:[],evidenceIds:[],responses:[],history:[]})
 let resolve,reject;const response=new Promise((a,b)=>{resolve=a;reject=b})
 const modules={react,'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[new URLSearchParams('case=SYNTHETIC&id=A')]},'../api':{api:{post:()=>{sent++;return response}},ApiError:class extends Error{},CASE_ID:'SYNTHETIC',casePath:(p,c)=>`/cases/${c}${p}`,getRole:()=> 'synthetic',getOperator:()=> 'synthetic',onIdentityChange:()=>()=>{}},'../recommendationReview/RecommendationReview':{RecommendationReview:()=>null},'../consultation/ConsultationPanel':{ConsultationPanel:()=>null},'../config':{SERVICE_ADDR:'synthetic'},'../components/Panel':{Panel:()=>null,Metric:()=>null},'../components/Toast':toast,'../format':{daysUntil:()=>0,toLocal:v=>v},'../recommendationReview/useBoardLoad':{useLoad:()=>({data:loadIndex++===0?{}:loadIndex===2?{columns:[{key:'Closed',items:[rec('A'),rec('B')]}],allowed:{Responded:['Implemented']}}:[],reload:()=>reloads++})}}
 const page=evaluate(pageCode,modules);const root=page.RecommendationsPage();values=[]
 const render=()=>{index=0;loadIndex=0;return root.type(root.props)}
 const detail=()=>nodes(render()).find(n=>n.type?.name==='Detail')
 function drop(id){nodes(render()).find(n=>n.props?.onDrop).props.onDrop({preventDefault(){},dataTransfer:{getData:()=>id}})}
 drop('A');const a=detail();assert.equal(a.props.pending,'Implemented')
 let work
 if(reply){
   const parentValues=values;let detailValues=[]
   function renderDetail(){values=detailValues;index=0;const t=a.type(a.props);detailValues=values;values=parentValues;return t}
   nodes(renderDetail()).find(n=>n.props?.placeholder==='回复内容').props.onChange({target:{value:'synthetic reply'}})
   work=nodes(renderDetail()).find(n=>n.type==='button'&&n.props.children==='登记回复').props.onClick()
 }else work=a.props.onTransition('A','Implemented','synthetic')
 if(change==='other')drop('B')
 if(change==='aba'){drop('B');drop('A')}
 if(change==='case')for(const f of cleanups)f()
 if(failure)reject(new Error('synthetic ordinary transport failure'));else resolve(rec('A'))
 await work
 if(change==='other'||change==='aba')assert.equal(detail().props.pending,'Implemented','old completion must retain newer confirmation')
 else if(change==='normal')assert.equal(detail().props.pending,failure?'Implemented':null)
 assert.equal(notices.length,change==='case'?0:1)
 if(change!=='case')assert.equal(notices[0][1],failure?'err':'ok')
 if(change==='case')assert.equal(reloads,0)
 assert.equal(sent,1)
}
;(async()=>{for(const change of ['normal','other','aba','case'])for(const failure of [false,true])await scenario(change,failure);for(const change of ['normal','other','case'])for(const failure of [false,true])await scenario(change,failure,true);console.log('Recommendation pending: 14 synthetic parent/reply lifecycle scenarios passed')})().catch(e=>{console.error(e);process.exitCode=1})

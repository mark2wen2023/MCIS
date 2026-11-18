// Actual parent refresh, Detail and useScopedActions; synthetic hooks/read loader/promises. No HTTP/browser.
const assert=require('node:assert/strict'),vm=require('node:vm'),{buildSync}=require('esbuild')
const bundle=p=>buildSync({entryPoints:[p],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const pageCode=bundle('src/pages/RecommendationsPage.tsx'),toastCode=bundle('src/components/Toast.tsx')
const jsx=(type,props,key)=>({type,props,key})
function evaluate(code,modules){const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}});return box.exports}
function nodes(n){if(!n)return[];if(Array.isArray(n))return n.flatMap(nodes);return typeof n==='object'?[n,...nodes(n.props?.children)]:[]}
async function scenario(mode){
 let values=[],index=0,loadIndex=0,cleanups=[],effects=[];const notices=[]
 const react={useLayoutEffect:(f,deps)=>{const store=values,i=index++,old=store[i];if(!old||!deps||deps.some((v,j)=>!Object.is(v,old.deps?.[j])))effects.push(()=>{old?.cleanup?.();const c=f();store[i]={deps,cleanup:c};if(c)cleanups.push(c)})},useRef:v=>{const store=values,i=index++;if(!(i in store))store[i]={current:v};return store[i]},useState:v=>{const store=values,i=index++;if(!(i in store))store[i]=v;return[store[i],v=>store[i]=typeof v==='function'?v(store[i]):v]},useSyncExternalStore:(_,f)=>f(),createContext:()=>({}),useContext:()=>((...n)=>notices.push(n)),useCallback:f=>f}
 const toast=evaluate(toastCode,{react,'react/jsx-runtime':{jsx,jsxs:jsx},'../api':{ApiError:class extends Error{}}})
 const rec={id:'REC-SYNTHETIC',status:'Responded',column:'Draft',progressPct:25,addressee:'synthetic',causeNodeIds:[],evidenceIds:[],responses:[],history:[]}
 let boardRec=rec,readState='ready',reloads=0
 let resolve,reject;const response=new Promise((a,b)=>{resolve=a;reject=b});const sent=[]
 const api={post:(path,body)=>{sent.push({path,body});return response},patch:(path,body)=>{sent.push({path,body});return response}}
 const modules={react,'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[new URLSearchParams('case=SYNTHETIC&id=REC-SYNTHETIC')]},'../api':{api,ApiError:class extends Error{},CASE_ID:'SYNTHETIC',casePath:(p,c)=>`/cases/${c}${p}`,getRole:()=> 'synthetic',getOperator:()=> 'synthetic',onIdentityChange:()=>()=>{}},'../recommendationReview/RecommendationReview':{RecommendationReview:()=>null},'../consultation/ConsultationPanel':{ConsultationPanel:()=>null},'../config':{SERVICE_ADDR:'synthetic'},'../components/Panel':{Panel:()=>null,Metric:()=>null},'../components/Toast':toast,'../format':{daysUntil:()=>0,toLocal:v=>v},'../recommendationReview/useBoardLoad':{useLoad:()=>({reload:()=>{reloads++},loading:readState==='loading',error:readState==='failure'?'synthetic read failure':null,data:loadIndex++===0?{}:loadIndex===2?{columns:[{key:'Draft',items:[boardRec]}],allowed:{Responded:['NotAdopted']}}:[]})}}
 const commit=()=>{for(const f of effects.splice(0))f()};
 const page=evaluate(pageCode,modules);let root=page.RecommendationsPage();let tree=root.type(root.props);commit()
 const detail=nodes(tree).find(n=>n.type?.name==='Detail');assert.ok(detail)
 detail.props.onCancel=()=>{}
 const parentValues=values;values=[];cleanups=[]
 const render=()=>{index=0;const result=detail.type(detail.props);commit();return result}
 function updateFromParent(){const detailValues=values;values=parentValues;index=0;loadIndex=0;const next=root.type(root.props);commit();const nextDetail=nodes(next).find(n=>n.type?.name==='Detail');assert.equal(nextDetail.key,detail.key);detail.props=nextDetail.props;values=detailValues}
 const input=(tree,placeholder)=>nodes(tree).find(n=>n.type==='input'&&n.props.placeholder===placeholder)
 const range=()=>nodes(render()).find(n=>n.type==='input'&&n.props.type==='range')
 const note=()=>input(render(),'说明（未采纳必填）')
 const save=()=>nodes(render()).find(n=>n.type==='button'&&n.props.children==='保存进度')
 assert.equal(range().props.value,25)
 note().props.onChange({target:{value:'synthetic preserved draft'}})
 range().props.onChange({target:{value:'35'}})
 if(mode==='adopt'){
  boardRec={...rec,progressPct:50,updatedUtc:'synthetic-new'};updateFromParent()
 }
 const before=range().props.value
 const button=mode==='adopt'?nodes(render()).find(n=>n.type==='button'&&n.props.children==='采用当前已读取进度，保留说明'):save()
 assert.equal(button.props.disabled,false,'old action is eligible before reload')
 if(mode==='unknown'){
  const work=button.props.onClick();reject(new Error('synthetic ordinary communication error'));await work
 }
 const oldAction=button.props.onClick
 // Execute actual parent refresh; loader.reload is a counted stub, not the real hook.
 // This isolates the parent-to-Detail callback window without claiming React scheduler coverage.
 // Deliberately DO NOT render parent or Detail before invoking the captured action.
 detail.props.onChanged();assert.equal(reloads,2,'board and audit reload callbacks were called')
 const late=oldAction()
 assert.equal(sent.length,mode==='unknown'?1:0,'reload-to-render window must not dispatch')
 await late
 assert.equal(range().props.value,before,'old adoption must not change the draft')
 assert.equal(note().props.value,'synthetic preserved draft')
 if(mode==='unknown')assert.equal(save().props.disabled,true,'reload cannot unlock unknown')
 readState='loading';updateFromParent();render()
 assert.equal(range().props.value,before);assert.equal(note().props.value,'synthetic preserved draft')
 readState='failure';updateFromParent();render()
 assert.equal(range().props.value,before);assert.equal(note().props.value,'synthetic preserved draft')
 if(mode!=='unknown'){
  readState='ready';updateFromParent();render()
  if(mode==='adopt'){
   nodes(render()).find(n=>n.type==='button'&&n.props.children==='采用当前已读取进度，保留说明').props.onClick()
   assert.equal(range().props.value,50);assert.equal(note().props.value,'synthetic preserved draft')
  }else{
   const work=save().props.onClick();assert.equal(sent.length,1);resolve(rec);await work
  }
 }
}
let complete=false;process.on('beforeExit',()=>{if(!complete){console.error('FAIL: reload scenarios unfinished');process.exitCode=1}})
;(async()=>{for(const mode of (process.argv[2]?[process.argv[2]]:['save','adopt','unknown']))await scenario(mode);complete=true;console.log('Reload action window: 3 synthetic component cases passed')})().catch(e=>{console.error(e);process.exitCode=1})

// Actual parent refresh, Detail and useScopedActions; synthetic hooks/read loader/promises. No HTTP/browser.
const assert=require('node:assert/strict'),vm=require('node:vm'),{buildSync}=require('esbuild')
const bundle=p=>buildSync({entryPoints:[p],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const pageCode=bundle('src/pages/RecommendationsPage.tsx'),toastCode=bundle('src/components/Toast.tsx')
const jsx=(type,props,key)=>({type,props,key})
function evaluate(code,modules){const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}});return box.exports}
function nodes(n){if(!n)return[];if(Array.isArray(n))return n.flatMap(nodes);return typeof n==='object'?[n,...nodes(n.props?.children)]:[]}
async function scenario(mode){
 let values=[],index=0,loadIndex=0,cleanups=[];const notices=[]
 const react={useLayoutEffect:f=>{const i=index++;if(!(i in values)){values[i]=true;const c=f();if(c)cleanups.push(c)}},useRef:v=>{const store=values,i=index++;if(!(i in store))store[i]={current:v};return store[i]},useState:v=>{const store=values,i=index++;if(!(i in store))store[i]=v;return[store[i],v=>store[i]=typeof v==='function'?v(store[i]):v]},useSyncExternalStore:(_,f)=>f(),createContext:()=>({}),useContext:()=>((...n)=>notices.push(n)),useCallback:f=>f}
 const toast=evaluate(toastCode,{react,'react/jsx-runtime':{jsx,jsxs:jsx},'../api':{ApiError:class extends Error{}}})
 const rec={id:'REC-SYNTHETIC',status:'Responded',column:'Draft',progressPct:25,addressee:'synthetic',causeNodeIds:[],evidenceIds:[],responses:[],history:[]}
 let boardRec=rec,readState='ready',reloads=0
 let resolve,reject;const response=new Promise((a,b)=>{resolve=a;reject=b});const sent=[]
 const api={post:(path,body)=>{sent.push({path,body});return response},patch:(path,body)=>{sent.push({path,body});return response}}
 const modules={react,'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[new URLSearchParams('case=SYNTHETIC&id=REC-SYNTHETIC')]},'../api':{api,ApiError:class extends Error{},CASE_ID:'SYNTHETIC',casePath:(p,c)=>`/cases/${c}${p}`,getRole:()=> 'synthetic',getOperator:()=> 'synthetic',onIdentityChange:()=>()=>{}},'../recommendationReview/RecommendationReview':{RecommendationReview:()=>null},'../consultation/ConsultationPanel':{ConsultationPanel:()=>null},'../config':{SERVICE_ADDR:'synthetic'},'../components/Panel':{Panel:()=>null,Metric:()=>null},'../components/Toast':toast,'../format':{daysUntil:()=>0,toLocal:v=>v},'../recommendationReview/useBoardLoad':{useLoad:()=>({reload:()=>{reloads++},loading:readState==='loading',error:readState==='failure'?'synthetic read failure':null,data:loadIndex++===0?{}:loadIndex===2?{columns:[{key:'Draft',items:[boardRec]}],allowed:{Responded:['NotAdopted']}}:[]})}}
 const page=evaluate(pageCode,modules);let root=page.RecommendationsPage();let tree=root.type(root.props)
 const detail=nodes(tree).find(n=>n.type?.name==='Detail');assert.ok(detail)
 detail.props.onCancel=()=>{}
 const parentValues=values;values=[];cleanups=[]
 const render=()=>{index=0;return detail.type(detail.props)}
 function updateFromParent(){const detailValues=values;values=parentValues;index=0;loadIndex=0;const next=root.type(root.props);const nextDetail=nodes(next).find(n=>n.type?.name==='Detail');assert.equal(nextDetail.key,detail.key);detail.props=nextDetail.props;values=detailValues}
 const input=(tree,placeholder)=>nodes(tree).find(n=>n.type==='input'&&n.props.placeholder===placeholder)
 const range=()=>nodes(render()).find(n=>n.type==='input'&&n.props.type==='range')
 const note=()=>input(render(),'说明（未采纳必填）')
 const save=()=>nodes(render()).find(n=>n.type==='button'&&n.props.children==='保存进度')
 const changed=()=>nodes(render()).some(n=>typeof n.props?.children==='string'&&n.props.children.startsWith('来源数据已变化'))
 const adopt=()=>nodes(render()).find(n=>n.type==='button'&&n.props.children==='采用当前已读取进度，保留说明')
 note().props.onChange({target:{value:'synthetic retained note'}})
 range().props.onChange({target:{value:'35'}})
 const oldSave=save().props.onClick
 if(mode==='unknown'){const work=oldSave();reject(new Error('synthetic communication failure'));await work}
 if(mode==='same'){
  for(let i=0;i<3;i++){boardRec={...rec};updateFromParent();render();assert.equal(changed(),false)}
  assert.equal(save().props.disabled,false);assert.equal(note().props.value,'synthetic retained note');return
 }
 const observe=r=>{
  if(mode!=='callback')detail.props.onChanged()
  boardRec=r;readState='ready';updateFromParent();render()
 }
 observe({...rec,progressPct:50,updatedUtc:'synthetic-B'})
 assert.equal(changed(),true);assert.equal(range().props.value,35)
 const oldAdopt=adopt().props.onClick
 observe({...rec}) // Return ALL compared fields to A, not just its percentage.
 assert.equal(changed(),true,'observed A-B-A must keep draft review notice')
 assert.equal(save().props.disabled,true)
 const late=oldSave();assert.equal(sent.length,mode==='unknown'?1:0);await late
 oldAdopt();assert.equal(range().props.value,35,'stale adoption must not change draft')
 if(mode==='unknown'){
  assert.equal(adopt().props.disabled,true);adopt().props.onClick()
  assert.equal(changed(),true);assert.equal(save().props.disabled,true)
 }else{
  for(const state of ['loading','failure']){readState=state;updateFromParent();render();assert.equal(changed(),true);adopt().props.onClick();assert.equal(range().props.value,35)}
  readState='ready';updateFromParent();render()
  assert.equal(adopt().props.disabled,false);adopt().props.onClick()
  assert.equal(changed(),false);assert.equal(range().props.value,25)
  assert.equal(note().props.value,'synthetic retained note','explicit adoption retains the note')
  assert.equal(save().props.disabled,true,'same percentage note cannot be independently saved')
  range().props.onChange({target:{value:'40'}})
  const work=save().props.onClick();assert.equal(sent.length,1);assert.equal(sent[0].body.note,'synthetic retained note');resolve(rec);await work
 }
 if(mode==='unknown')assert.equal(note().props.value,'synthetic retained note')
}
;(async()=>{for(const mode of ['aba','same','unknown','callback'])await scenario(mode);console.log('Observed source generation: 4 synthetic scenarios passed')})().catch(e=>{console.error(e);process.exitCode=1})

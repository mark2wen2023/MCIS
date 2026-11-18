// Actual Detail and actual useScopedActions.run; synthetic hooks/promises. No HTTP/browser.
const assert=require('node:assert/strict'),vm=require('node:vm'),{buildSync}=require('esbuild')
const bundle=p=>buildSync({entryPoints:[p],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const pageCode=bundle('src/pages/RecommendationsPage.tsx'),toastCode=bundle('src/components/Toast.tsx')
const jsx=(type,props,key)=>({type,props,key})
function evaluate(code,modules){const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}});return box.exports}
function nodes(n){if(!n)return[];if(Array.isArray(n))return n.flatMap(nodes);return typeof n==='object'?[n,...nodes(n.props?.children)]:[]}
async function scenario(mode){
 let values=[],index=0,loadIndex=0;const notices=[]
 const react={useLayoutEffect:f=>{f()},useRef:v=>{const store=values,i=index++;if(!(i in store))store[i]={current:v};return store[i]},useState:v=>{const store=values,i=index++;if(!(i in store))store[i]=v;return[store[i],v=>store[i]=typeof v==='function'?v(store[i]):v]},useSyncExternalStore:(_,f)=>f(),createContext:()=>({}),useContext:()=>((...n)=>notices.push(n)),useCallback:f=>f}
 const toast=evaluate(toastCode,{react,'react/jsx-runtime':{jsx,jsxs:jsx},'../api':{ApiError:class extends Error{}}})
 const rec={id:'REC-SYNTHETIC',status:'Responded',column:'Draft',progressPct:25,addressee:'synthetic',causeNodeIds:[],evidenceIds:[],responses:[],history:[]}
 let boardRec=rec,readState='ready'
 let resolve,reject;const response=new Promise((a,b)=>{resolve=a;reject=b});const sent=[]
 const api={post:(path,body)=>{sent.push({path,body});return response},patch:(path,body)=>{sent.push({path,body});return response}}
 const modules={react,'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[new URLSearchParams('case=SYNTHETIC&id=REC-SYNTHETIC')]},'../api':{api,ApiError:class extends Error{},CASE_ID:'SYNTHETIC',casePath:(p,c)=>`/cases/${c}${p}`,getRole:()=> 'synthetic',getOperator:()=> 'synthetic',onIdentityChange:()=>()=>{}},'../recommendationReview/RecommendationReview':{RecommendationReview:()=>null},'../consultation/ConsultationPanel':{ConsultationPanel:()=>null},'../config':{SERVICE_ADDR:'synthetic'},'../components/Panel':{Panel:()=>null,Metric:()=>null},'../components/Toast':toast,'../format':{daysUntil:()=>0,toLocal:v=>v},'../recommendationReview/useBoardLoad':{useLoad:()=>({loading:readState==='loading',error:readState==='failure'?'synthetic read failure':null,data:loadIndex++===0?{}:loadIndex===2?{columns:[{key:'Draft',items:[boardRec]}],allowed:{Responded:['NotAdopted']}}:[]})}}
 const page=evaluate(pageCode,modules);let root=page.RecommendationsPage();let tree=root.type(root.props)
 const detail=nodes(tree).find(n=>n.type?.name==='Detail');assert.ok(detail)
 detail.props.onChanged=()=>{};detail.props.onCancel=()=>{}
 const parentValues=values;values=[]
 const render=()=>{index=0;return detail.type(detail.props)}
 function updateFromParent(){const detailValues=values;values=parentValues;index=0;loadIndex=0;const next=root.type(root.props);const nextDetail=nodes(next).find(n=>n.type?.name==='Detail');assert.equal(nextDetail.key,detail.key);detail.props=nextDetail.props;values=detailValues}
 const input=(tree,placeholder)=>nodes(tree).find(n=>n.type==='input'&&n.props.placeholder===placeholder)
 const range=()=>nodes(render()).find(n=>n.type==='input'&&n.props.type==='range')
 const note=()=>input(render(),'说明（未采纳必填）')
 const save=()=>nodes(render()).find(n=>n.type==='button'&&n.props.children==='保存进度')
 assert.equal(range().props.value,25)
 if(mode!=='clean')note().props.onChange({target:{value:'synthetic unsaved note'}})
 if(['edited','unknown'].includes(mode))range().props.onChange({target:{value:'35'}})
 let pending
 if(mode==='unknown'){pending=save().props.onClick();reject(new Error('synthetic transport failure'));await pending}
 // Reload pending / ordinary read failure retains exact old props. Same mounted Detail.
 const before=range().props.value
 readState='loading';updateFromParent();render();readState='failure';updateFromParent();render()
 assert.equal(range().props.value,before)
 if(mode!=='clean')assert.equal(note().props.value,'synthetic unsaved note')
 boardRec={...rec,progressPct:50,updatedUtc:'synthetic-new-observation'};readState='ready';updateFromParent()
 if(mode==='clean') {assert.equal(range().props.value,50,'unmodified control must follow same-ID new snapshot');assert.equal(save().props.disabled,true)}
 else {
  assert.equal(range().props.value,mode==='note'?25:35)
  assert.equal(note().props.value,'synthetic unsaved note')
  assert.ok(nodes(render()).some(n=>typeof n.props?.children==='string'&&n.props.children.includes('来源数据已变化')))
 }
 if(mode==='unknown'){assert.equal(save().props.disabled,true);await save().props.onClick();assert.equal(sent.length,1)}
 else assert.equal(sent.length,0,'reading never submits')
}
;(async()=>{for(const mode of ['clean','edited','note','unknown'])await scenario(mode);console.log('Progress snapshot: 4 continuous synthetic Detail cases passed')})().catch(e=>{console.error(e);process.exitCode=1})

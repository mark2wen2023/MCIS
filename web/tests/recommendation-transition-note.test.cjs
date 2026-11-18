// Actual Detail and actual useToast.run; synthetic hooks/promises. No HTTP/browser.
const assert=require('node:assert/strict'),vm=require('node:vm'),{buildSync}=require('esbuild')
const bundle=p=>buildSync({entryPoints:[p],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const pageCode=bundle('src/pages/RecommendationsPage.tsx'),toastCode=bundle('src/components/Toast.tsx')
const jsx=(type,props,key)=>({type,props,key})
function evaluate(code,modules){const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}});return box.exports}
function nodes(n){if(!n)return[];if(Array.isArray(n))return n.flatMap(nodes);return typeof n==='object'?[n,...nodes(n.props?.children)]:[]}
async function scenario(mode,editDuring=false){
 let values=[],index=0,loadIndex=0;const notices=[]
 const react={useState:v=>{const store=values,i=index++;if(!(i in store))store[i]=v;return[store[i],v=>store[i]=typeof v==='function'?v(store[i]):v]},useSyncExternalStore:(_,f)=>f(),createContext:()=>({}),useContext:()=>((...n)=>notices.push(n)),useCallback:f=>f}
 const toast=evaluate(toastCode,{react,'react/jsx-runtime':{jsx,jsxs:jsx},'../api':{ApiError:class extends Error{}}})
 const rec={id:'REC-SYNTHETIC',status:'Draft',column:'Draft',progressPct:0,addressee:'synthetic',causeNodeIds:[],evidenceIds:[],responses:[],history:[]}
 const modules={react,'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[new URLSearchParams('case=SYNTHETIC&id=REC-SYNTHETIC')]},'../api':{CASE_ID:'SYNTHETIC',casePath:(p,c)=>`/cases/${c}${p}`,getRole:()=> 'synthetic',getOperator:()=> 'synthetic',onIdentityChange:()=>()=>{}},'../recommendationReview/RecommendationReview':{RecommendationReview:()=>null},'../consultation/ConsultationPanel':{ConsultationPanel:()=>null},'../config':{SERVICE_ADDR:'synthetic'},'../components/Panel':{Panel:()=>null,Metric:()=>null},'../components/Toast':toast,'../format':{daysUntil:()=>0,toLocal:v=>v},'../hooks':{useLoad:()=>({data:loadIndex++===0?{}:loadIndex===2?{columns:[{key:'Draft',items:[rec]}],allowed:{Draft:['NotAdopted']}}:[]})}}
 const page=evaluate(pageCode,modules);let root=page.RecommendationsPage();let tree=root.type(root.props)
 const detail=nodes(tree).find(n=>n.type?.name==='Detail');assert.ok(detail)
 let resolve,reject;const response=new Promise((a,b)=>{resolve=a;reject=b})
 detail.props.onTransition=()=>toast.useToast().run(()=>response,'synthetic saved')
 values=[]
 const render=()=>{index=0;return detail.type(detail.props)}
 const input=tree=>nodes(tree).find(n=>n.type==='input'&&n.props.placeholder==='说明（未采纳必填）')
 input(render()).props.onChange({target:{value:'unsaved explanation'}})
 const button=nodes(render()).find(n=>n.type==='button'&&n.props.className?.includes('btn-danger'))
 const pending=button.props.onClick()
 if(editDuring)input(render()).props.onChange({target:{value:'newer explanation'}})
 if(mode==='failure')reject(new Error('synthetic transport unavailable'));else resolve(rec)
 await pending
 const expected=editDuring?'newer explanation':mode==='failure'?'unsaved explanation':''
 assert.equal(input(render()).props.value,expected,'read current rendered input after completion')
 assert.equal(notices.at(-1)[1],mode==='failure'?'err':'ok')
}
;(async()=>{await scenario('failure');await scenario('success');await scenario('success',true);await scenario('failure',true);console.log('Recommendation note: 4 synthetic completion scenarios passed')})().catch(e=>{console.error(e);process.exitCode=1})

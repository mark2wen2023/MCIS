// Actual Detail and actual useScopedActions.run; synthetic hooks/promises. No HTTP/browser.
const assert=require('node:assert/strict'),vm=require('node:vm'),{buildSync}=require('esbuild')
const bundle=p=>buildSync({entryPoints:[p],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const pageCode=bundle('src/pages/RecommendationsPage.tsx'),toastCode=bundle('src/components/Toast.tsx')
const jsx=(type,props,key)=>({type,props,key})
function evaluate(code,modules){const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}});return box.exports}
function nodes(n){if(!n)return[];if(Array.isArray(n))return n.flatMap(nodes);return typeof n==='object'?[n,...nodes(n.props?.children)]:[]}
async function scenario(kind,mode,edit='none'){
 let values=[],index=0,loadIndex=0;const notices=[]
 const react={useLayoutEffect:f=>{f()},useRef:v=>{const store=values,i=index++;if(!(i in store))store[i]={current:v};return store[i]},useState:v=>{const store=values,i=index++;if(!(i in store))store[i]=v;return[store[i],v=>store[i]=typeof v==='function'?v(store[i]):v]},useSyncExternalStore:(_,f)=>f(),createContext:()=>({}),useContext:()=>((...n)=>notices.push(n)),useCallback:f=>f}
 const toast=evaluate(toastCode,{react,'react/jsx-runtime':{jsx,jsxs:jsx},'../api':{ApiError:class extends Error{}}})
 const rec={id:'REC-SYNTHETIC',status:'Responded',column:'Draft',progressPct:0,addressee:'synthetic',causeNodeIds:[],evidenceIds:[],responses:[],history:[]}
 let resolve,reject;const response=new Promise((a,b)=>{resolve=a;reject=b});const sent=[]
 const api={post:(path,body)=>{sent.push({path,body});return response},patch:(path,body)=>{sent.push({path,body});return response}}
 const modules={react,'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[new URLSearchParams('case=SYNTHETIC&id=REC-SYNTHETIC')]},'../api':{api,ApiError:class extends Error{},CASE_ID:'SYNTHETIC',casePath:(p,c)=>`/cases/${c}${p}`,getRole:()=> 'synthetic',getOperator:()=> 'synthetic',onIdentityChange:()=>()=>{}},'../recommendationReview/RecommendationReview':{RecommendationReview:()=>null},'../consultation/ConsultationPanel':{ConsultationPanel:()=>null},'../config':{SERVICE_ADDR:'synthetic'},'../components/Panel':{Panel:()=>null,Metric:()=>null},'../components/Toast':toast,'../format':{daysUntil:()=>0,toLocal:v=>v},'../hooks':{useLoad:()=>({data:loadIndex++===0?{}:loadIndex===2?{columns:[{key:'Draft',items:[rec]}],allowed:{Responded:['NotAdopted']}}:[]})}}
 const page=evaluate(pageCode,modules);let root=page.RecommendationsPage();let tree=root.type(root.props)
 const detail=nodes(tree).find(n=>n.type?.name==='Detail');assert.ok(detail)
 detail.props.onChanged=()=>{};detail.props.onCancel=()=>{}
 values=[]
 const render=()=>{index=0;return detail.type(detail.props)}
 const input=(tree,placeholder)=>nodes(tree).find(n=>n.type==='input'&&n.props.placeholder===placeholder)
 const field=kind==='reply'?'回复内容':'说明（未采纳必填）'
 const change=(placeholder,value)=>input(render(),placeholder).props.onChange({target:{value}})
 change(field,'submitted text')
 if(kind==='progress')nodes(render()).find(n=>n.type==='input'&&n.props.type==='range').props.onChange({target:{value:'25'}})
 const button=nodes(render()).find(n=>n.type==='button'&&n.props.children===(kind==='reply'?'登记回复':'保存进度'))
 const pending=button.props.onClick()
 assert.equal(sent.length,1)
 if(kind==='progress')assert.equal(sent[0].body.progressPct,25)
 assert.equal(kind==='reply'?sent[0].body.text:sent[0].body.note,'submitted text')
 if(edit==='different')change(field,'new draft')
 if(edit==='aba'){change(field,'intermediate');change(field,'submitted text')}
 if(edit==='percent')nodes(render()).find(n=>n.type==='input'&&n.props.type==='range').props.onChange({target:{value:'50'}})
 if(edit==='party')change('回复方','new party')
 if(mode==='failure')reject(new Error('synthetic transport unavailable'));else resolve(rec)
 await pending
 const expected=edit==='different'?'new draft':edit!=='none'||mode==='failure'?'submitted text':''
 assert.equal(input(render(),field).props.value,expected,'inspect current rendered input')
 if(edit==='percent')assert.equal(nodes(render()).find(n=>n.type==='input'&&n.props.type==='range').props.value,50)
 assert.equal(notices.at(-1)[1],mode==='failure'?'err':'ok')
}
;(async()=>{
 for(const kind of ['reply','progress'].filter(k=>!process.argv[2]||process.argv[2]===k)){await scenario(kind,'success','different');await scenario(kind,'success');await scenario(kind,'failure');await scenario(kind,'success','aba')}
 if(!process.argv[2]||process.argv[2]==='reply')await scenario('reply','success','party')
 if(!process.argv[2]||process.argv[2]==='progress')await scenario('progress','success','percent')
 console.log('Recommendation form saves: 10 synthetic scenarios passed')
})().catch(e=>{console.error(e);process.exitCode=1})

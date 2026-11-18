// Actual Detail and actual scoped action handling; synthetic hooks/promises. No HTTP/browser.
const assert=require('node:assert/strict'),vm=require('node:vm'),{buildSync}=require('esbuild')
const bundle=p=>buildSync({entryPoints:[p],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const pageCode=bundle('src/pages/RecommendationsPage.tsx'),toastCode=bundle('src/components/Toast.tsx')
const jsx=(type,props,key)=>({type,props,key})
function evaluate(code,modules){const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}});return box.exports}
function nodes(n){if(!n)return[];if(Array.isArray(n))return n.flatMap(nodes);return typeof n==='object'?[n,...nodes(n.props?.children)]:[]}
async function scenario(kind,mode,edit='none'){
 let values=[],index=0,loadIndex=0,cleanups=[];const notices=[]
 const react={useLayoutEffect:f=>{const i=index++;if(!(i in values)){values[i]=true;const c=f();if(c)cleanups.push(c)}},useRef:v=>{const store=values,i=index++;if(!(i in store))store[i]={current:v};return store[i]},useState:v=>{const store=values,i=index++;if(!(i in store))store[i]=v;return[store[i],v=>store[i]=typeof v==='function'?v(store[i]):v]},useSyncExternalStore:(_,f)=>f(),createContext:()=>({}),useContext:()=>((...n)=>notices.push(n)),useCallback:f=>f}
 const toast=evaluate(toastCode,{react,'react/jsx-runtime':{jsx,jsxs:jsx},'../api':{ApiError:class extends Error{}}})
 const rec={id:'REC-SYNTHETIC',status:'Responded',column:'Draft',progressPct:0,addressee:'synthetic',causeNodeIds:[],evidenceIds:[],responses:[],history:[]}
 let resolve,reject;const response=new Promise((a,b)=>{resolve=a;reject=b});const sent=[]
 const api={post:(path,body)=>{sent.push({path,body});return response},patch:(path,body)=>{sent.push({path,body});return response}}
 const modules={react,'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[new URLSearchParams('case=SYNTHETIC&id=REC-SYNTHETIC')]},'../api':{api,ApiError:class extends Error{},CASE_ID:'SYNTHETIC',casePath:(p,c)=>`/cases/${c}${p}`,getRole:()=> 'synthetic',getOperator:()=> 'synthetic',onIdentityChange:()=>()=>{}},'../recommendationReview/RecommendationReview':{RecommendationReview:()=>null},'../consultation/ConsultationPanel':{ConsultationPanel:()=>null},'../config':{SERVICE_ADDR:'synthetic'},'../components/Panel':{Panel:()=>null,Metric:()=>null},'../components/Toast':toast,'../format':{daysUntil:()=>0,toLocal:v=>v},'../recommendationReview/useBoardLoad':{useLoad:()=>({data:loadIndex++===0?{}:loadIndex===2?{columns:[{key:'Draft',items:[rec]}],allowed:{Responded:['NotAdopted']}}:[]})}}
 const page=evaluate(pageCode,modules);let root=page.RecommendationsPage();let tree=root.type(root.props)
 const detail=nodes(tree).find(n=>n.type?.name==='Detail');assert.ok(detail)
 let refreshCalls=0
 detail.props.onChanged=()=>{refreshCalls++;if(mode==='refresh-throw')throw new Error('synthetic refresh callback failed')};detail.props.onCancel=()=>{}
 values=[];cleanups=[]
 const render=()=>{index=0;return detail.type(detail.props)}
 const input=(tree,placeholder)=>nodes(tree).find(n=>n.type==='input'&&n.props.placeholder===placeholder)
 const field=kind==='reply'?'回复内容':'说明（未采纳必填）'
 const change=(placeholder,value)=>input(render(),placeholder).props.onChange({target:{value}})
 change(field,'submitted text')
 if(kind==='progress')nodes(render()).find(n=>n.type==='input'&&n.props.type==='range').props.onChange({target:{value:'25'}})
 const button=nodes(render()).find(n=>n.type==='button'&&n.props.children===(kind==='reply'?'登记回复':'保存进度'))
 const pending=button.props.onClick()
 const duplicate=button.props.onClick();void duplicate
 assert.equal(sent.length,1,'second click before rerender must not dispatch')
 if(kind==='progress')assert.equal(sent[0].body.progressPct,25)
 assert.equal(kind==='reply'?sent[0].body.text:sent[0].body.note,'submitted text')
 if(edit==='different')change(field,'new draft')
 if(edit==='aba'){change(field,'intermediate');change(field,'submitted text')}
 if(edit==='percent')nodes(render()).find(n=>n.type==='input'&&n.props.type==='range').props.onChange({target:{value:'50'}})
 if(edit==='party')change('回复方','new party')
 const waiting=nodes(render()).find(n=>n.type==='button'&&n.props.children==='保存进度')
 assert.equal(waiting.props.disabled,true)
 assert.ok(!input(render(),field).props.disabled&&!input(render(),field).props.readOnly)
 await waiting.props.onClick();assert.equal(sent.length,1,'editing while pending cannot dispatch a second request')
 if(mode==='unmount')for(const f of cleanups)f()
 if(mode==='failure')reject(new Error('synthetic transport unavailable'));else resolve(rec)
 await pending
 const expected=edit==='different'?'new draft':edit!=='none'||(mode==='failure'||mode==='unmount'||mode==='refresh-throw')?'submitted text':''
 assert.equal(input(render(),field).props.value,expected,'inspect current rendered input')
 if(edit==='percent')assert.equal(nodes(render()).find(n=>n.type==='input'&&n.props.type==='range').props.value,50)
 if(mode==='unmount'){assert.equal(notices.length,0);return}
 assert.equal(notices.at(-1)[1],['failure','refresh-throw'].includes(mode)?'err':'ok')
 const save=nodes(render()).find(n=>n.type==='button'&&n.props.children==='保存进度')
 if(['failure','refresh-throw'].includes(mode)){
  assert.equal(save.props.disabled,true)
  assert.ok(nodes(render()).some(n=>typeof n.props?.children==='string'&&n.props.children.includes('结果未知')))
  assert.ok(nodes(render()).some(n=>typeof n.props?.children==='string'&&n.props.children.includes('没有原地解锁')))
  await save.props.onClick();assert.equal(sent.length,1,'unknown result must not retry')
 }
 if(mode==='success')assert.ok(nodes(render()).some(n=>typeof n.props?.children==='string'&&n.props.children.includes('尚未确认读回')))
 if(mode==='refresh-throw')assert.equal(refreshCalls,1,'successful response reached refresh callback')
 if(edit==='percent'&&mode!=='refresh-throw')assert.ok(nodes(render()).some(n=>typeof n.props?.children==='string'&&n.props.children.includes('尚未保存')))

}
;(async()=>{await scenario('progress','success');await scenario('progress','success','percent');await scenario('progress','success','aba');await scenario('progress','failure','different');await scenario('progress','unmount');await scenario('progress','refresh-throw');await scenario('progress','refresh-throw','different');console.log('Progress flight: 7 synthetic scenarios passed')})().catch(e=>{console.error(e);process.exitCode=1})

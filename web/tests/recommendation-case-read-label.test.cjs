// Actual page evaluation with synthetic hooks and load states; no HTTP/browser or writes.
const assert = require('node:assert/strict')
const vm = require('node:vm')
const { buildSync } = require('esbuild')
const code = buildSync({entryPoints:['src/pages/RecommendationsPage.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const jsx=(type,props,key)=>({type,props,key})
function scenario(query,mode='ready') {
 const params=new URLSearchParams(query),values=[],loads=[],row={id:'REC-PRESENT',status:'Draft',column:'Draft',progressPct:0,addressee:'synthetic',causeNodeIds:[],evidenceIds:[],responses:[],history:[]}
 let i=0,li=0;const reloads=[0,0,0]
 const board={columns:[{key:'Draft',title:'draft',items:[row]}],allowed:{Draft:[]}}
 const modules={
  react:{useLayoutEffect:()=>{},useRef:v=>{const n=i++;if(!(n in values))values[n]={current:v};return values[n]},useState:v=>{const n=i++;if(!(n in values))values[n]=v;return[values[n],v=>values[n]=v]},useSyncExternalStore:(_,snapshot)=>snapshot()},
  'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[params,()=>{}]},
  '../api':{CASE_ID:'SYNTHETIC',casePath:(p,c)=>`/cases/${c}${p}`,getRole:()=> 'synthetic-role',getOperator:()=> 'synthetic-operator',onIdentityChange:()=>()=>{}},
  '../recommendationReview/RecommendationReview':{RecommendationReview:()=>null},'../consultation/ConsultationPanel':{ConsultationPanel:()=>null},
  '../config':{SERVICE_ADDR:'synthetic'},'../components/Panel':{Panel:()=>null,Metric:()=>null},
  '../components/Toast':{useToast:()=>({run:()=>{throw Error('unexpected mutation')},show:()=>{}})},'../format':{daysUntil:()=>0,toLocal:v=>v},
  '../recommendationReview/useBoardLoad':{useLoad:()=>{const n=li++;return {reload:()=>reloads[n]++,data:n===0?(mode==='ready'?{isFictionalDemo:true}:null):n===1?board:[],loading:n===0&&mode==='loading',error:n===0&&mode==='error'?'synthetic connection failure':null}}}
 }
 const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}})
 function render(){i=0;li=0;const root=box.exports.RecommendationsPage();return root.type(root.props)}
 function nodes(n){if(!n)return[];if(Array.isArray(n))return n.flatMap(nodes);return typeof n==='object'?[n,...nodes(n.props?.children)]:[]}
 function text(n){if(!n)return'';if(Array.isArray(n))return n.map(text).join('');return typeof n==='object'?text(n.props?.children):String(n)}
 return {render,nodes,text,reloads}
}
for(const mode of ['error','loading','ready']){
 const s=scenario('case=SYNTHETIC&id=REC-PRESENT',mode),tree=s.render()
 const tag=s.nodes(tree).find(n=>n.type==='span'&&n.props.className==='p6-tag')
 assert.equal(s.text(tag),mode==='error'?'案件信息读取失败':mode==='loading'?'案件信息加载中':'示例数据（虚构）')
 const button=s.nodes(tree).find(n=>n.type==='button'&&n.props.children==='重新读取看板与审计')
 button.props.onClick();assert.deepEqual(s.reloads,[0,1,1],'refresh does not retry case information')
 if(mode==='error')assert.match(s.text(tree),/该按钮不重读案件信息/)
}
console.log('Case read label: 3 synthetic page states passed')

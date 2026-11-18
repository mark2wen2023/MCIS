// Actual page evaluation with synthetic hooks and load states; no HTTP/browser or writes.
const assert = require('node:assert/strict')
const vm = require('node:vm')
const { buildSync } = require('esbuild')
const code = buildSync({entryPoints:['src/pages/RecommendationsPage.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const jsx=(type,props,key)=>({type,props,key})
function scenario(query,mode='ready') {
 const params=new URLSearchParams(query),values=[],loads=[],row={id:'REC-PRESENT',status:'Draft',column:'Draft',progressPct:0,addressee:'synthetic',causeNodeIds:[],evidenceIds:[],responses:[],history:[]}
 let i=0,li=0
 const board={columns:[{key:'Draft',title:'draft',items:[row]}],allowed:{Draft:[]}}
 const modules={
  react:{useLayoutEffect:()=>{},useRef:v=>{const n=i++;if(!(n in values))values[n]={current:v};return values[n]},useState:v=>{const n=i++;if(!(n in values))values[n]=v;return[values[n],v=>values[n]=v]},useSyncExternalStore:(_,snapshot)=>snapshot()},
  'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[params,()=>{}]},
  '../api':{CASE_ID:'SYNTHETIC',casePath:(p,c)=>`/cases/${c}${p}`,getRole:()=> 'synthetic-role',getOperator:()=> 'synthetic-operator',onIdentityChange:()=>()=>{}},
  '../recommendationReview/RecommendationReview':{RecommendationReview:()=>null},'../consultation/ConsultationPanel':{ConsultationPanel:()=>null},
  '../config':{SERVICE_ADDR:'synthetic'},'../components/Panel':{Panel:()=>null,Metric:()=>null},
  '../components/Toast':{useToast:()=>({run:()=>{throw Error('unexpected mutation')},show:()=>{}})},'../format':{daysUntil:()=>0,toLocal:v=>v},
  '../recommendationReview/useBoardLoad':{useLoad:()=>{const n=li++;loads.push(n);return n===0?{data:{isFictionalDemo:true}}:n===1?{data:['loading','error'].includes(mode)?null:board,loading:['loading','refreshing'].includes(mode),error:['error','stale-error'].includes(mode)?'synthetic unavailable':null}:{data:[],loading:mode==='refreshing',error:mode==='stale-error'?'synthetic audit failure':null}}}
 }
 const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}})
 function render(){i=0;li=0;const root=box.exports.RecommendationsPage();return root.type(root.props)}
 function nodes(n){if(!n)return[];if(Array.isArray(n))return n.flatMap(nodes);return typeof n==='object'?[n,...nodes(n.props?.children)]:[]}
 function text(n){if(!n)return'';if(Array.isArray(n))return n.map(text).join('');return typeof n==='object'?text(n.props?.children):String(n)}
 return {render,nodes,text}
}
for(const mode of ['loading','error','refreshing','stale-error','ready']){
 const s=scenario('case=SYNTHETIC&id=REC-PRESENT',mode),t=s.render(),txt=s.text(t)
 const metrics=s.nodes(t).filter(n=>n.props?.label==='安全建议')
 assert.equal(metrics.length,['loading','error'].includes(mode)?0:1,'unread is not zero')
 assert.match(txt,/不是同一时点快照/)
 if(mode==='refreshing'){assert.match(txt,/旧快照/);assert.match(txt,/审计正在重载/)}
 if(mode==='stale-error'){assert.match(txt,/重载失败/);assert.match(txt,/审计读取失败/)}
 if(['refreshing','stale-error','ready'].includes(mode)){
  const detail=s.nodes(t).find(n=>n.type?.name==='Detail');assert.equal(detail.key,'REC-PRESENT','retain Detail identity across read states')
 }
}
console.log('Recommendation read display: 5 synthetic page states passed (Detail identity checked, not browser)')

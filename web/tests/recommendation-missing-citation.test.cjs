// Actual page evaluation with synthetic hooks and load states; no HTTP/browser or writes.
const assert = require('node:assert/strict')
const vm = require('node:vm')
const { buildSync } = require('esbuild')
const code = buildSync({entryPoints:['src/pages/RecommendationsPage.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const jsx=(type,props,key)=>({type,props,key})
function scenario(query,mode='ready') {
 const params=new URLSearchParams(query),values=[],loads=[],row={id:'REC-PRESENT',status:'Draft',column:'Draft',progressPct:0}
 let i=0,li=0
 const board={columns:[{key:'Draft',title:'draft',items:[row]}],allowed:{Draft:[]}}
 const modules={
  react:{useState:v=>{const n=i++;if(!(n in values))values[n]=v;return[values[n],v=>values[n]=v]},useSyncExternalStore:(_,snapshot)=>snapshot()},
  'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[params,()=>{}]},
  '../api':{CASE_ID:'SYNTHETIC',casePath:(p,c)=>`/cases/${c}${p}`,getRole:()=> 'synthetic-role',getOperator:()=> 'synthetic-operator',onIdentityChange:()=>()=>{}},
  '../recommendationReview/RecommendationReview':{RecommendationReview:()=>null},'../consultation/ConsultationPanel':{ConsultationPanel:()=>null},
  '../config':{SERVICE_ADDR:'synthetic'},'../components/Panel':{Panel:()=>null,Metric:()=>null},
  '../components/Toast':{useToast:()=>({run:()=>{throw Error('unexpected mutation')},show:()=>{}})},'../format':{daysUntil:()=>0,toLocal:v=>v},
  '../hooks':{useLoad:()=>{const n=li++;loads.push(n);return n===0?{data:{isFictionalDemo:true}}:n===1?{data:mode==='loading'||mode==='error'?null:board,error:mode==='error'?'synthetic unavailable':null}:{data:[]}}}
 }
 const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}})
 function render(){i=0;li=0;const root=box.exports.RecommendationsPage();return root.type(root.props)}
 function nodes(n){if(!n)return[];if(Array.isArray(n))return n.flatMap(nodes);return typeof n==='object'?[n,...nodes(n.props?.children)]:[]}
 function text(n){if(!n)return'';if(Array.isArray(n))return n.map(text).join('');return typeof n==='object'?text(n.props?.children):String(n)}
 return {render,nodes,text}
}
const missing=scenario('case=SYNTHETIC&id=REC-MISSING')
let tree=missing.render()
assert.match(missing.text(tree),/当前案件看板未找到指定安全建议/)
assert.match(missing.text(tree),/REC-MISSING/)
assert.ok(missing.nodes(tree).some(n=>n.props?.role==='status'))
assert.ok(!missing.nodes(tree).some(n=>n.props?.recId),'no unrelated detail selected')
const card=missing.nodes(tree).find(n=>n.props?.rec?.id==='REC-PRESENT'&&n.props.onClick)
card.props.onClick();tree=missing.render()
assert.ok(!missing.text(tree).includes('当前案件看板未找到指定安全建议'))
assert.ok(missing.nodes(tree).some(n=>n.props?.recId==='REC-PRESENT'))
for(const mode of ['loading','error']){
 const s=scenario('case=SYNTHETIC&id=REC-MISSING',mode)
 assert.ok(!s.text(s.render()).includes('当前案件看板未找到指定安全建议'),mode)
}
for(const query of ['case=SYNTHETIC','case=SYNTHETIC&id=REC-PRESENT']){
 const s=scenario(query);assert.ok(!s.text(s.render()).includes('当前案件看板未找到指定安全建议'))
}
console.log('Recommendation citation: 6 synthetic states / 10 assertions passed')

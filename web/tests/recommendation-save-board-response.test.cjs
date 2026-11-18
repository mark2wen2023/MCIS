// Actual parent + Detail + useToast; synthetic hook scheduling and actual TestClient captures.
// No browser, concurrent HTTP connection, generated report, or authenticated identity claim.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),{buildSync}=require('esbuild')
const c=JSON.parse(fs.readFileSync(0,'utf8'))
const bundle=p=>buildSync({entryPoints:[p],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const jsx=(type,props,key)=>({type,props,key})
const nodes=n=>!n?[]:Array.isArray(n)?n.flatMap(nodes):typeof n==='object'?[n,...nodes(n.props?.children)]:[]
const evaluate=(code,modules)=>{const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}});return box.exports}
let state=[],index=0,loadIndex=0,board=c.initial,boardReloads=0,auditReloads=0,sent=0
const parentState=[],detailState=[],notices=[]
const react={useRef:v=>{const a=state,i=index++;if(!(i in a))a[i]={current:v};return a[i]},useState:v=>{const a=state,i=index++;if(!(i in a))a[i]=v;return[a[i],v=>a[i]=typeof v==='function'?v(a[i]):v]},useSyncExternalStore:(_,f)=>f(),createContext:()=>({}),useContext:()=>((...n)=>notices.push(n)),useCallback:f=>f}
const toast=evaluate(bundle('src/components/Toast.tsx'),{react,'react/jsx-runtime':{jsx,jsxs:jsx},'../api':{ApiError:class extends Error{}}})
const modules={react,'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[new URLSearchParams({case:c.case.caseId,id:c.rid})]},
 '../api':{api:{patch:async(path,body)=>{assert.equal(path,`/cases/${c.case.caseId}/recommendations/${c.rid}`);assert.deepEqual(JSON.parse(JSON.stringify(body)),c.body);sent++;return c.returned}},CASE_ID:'UNUSED',casePath:(p,id)=>`/cases/${id}${p}`,getRole:()=> 'synthetic',getOperator:()=> 'synthetic',onIdentityChange:()=>()=>{}},
 '../recommendationReview/RecommendationReview':{RecommendationReview:()=>null},'../consultation/ConsultationPanel':{ConsultationPanel:()=>null},'../config':{SERVICE_ADDR:'synthetic'},'../components/Panel':{Panel:()=>null,Metric:()=>null},'../components/Toast':toast,'../format':{daysUntil:()=>0,toLocal:v=>v},
 '../hooks':{useLoad:()=>{const n=loadIndex++;return n===0?{data:c.case}:n===1?{data:board,reload:()=>{boardReloads++;board=c.board}}:{data:[],reload:()=>auditReloads++}}}}
const page=evaluate(bundle('src/pages/RecommendationsPage.tsx'),modules)
function parent(){state=parentState;index=0;loadIndex=0;const root=page.RecommendationsPage();return root.type(root.props)}
function selected(tree){return nodes(tree).find(n=>n.type?.name==='Detail')}
function detail(node){state=detailState;index=0;return node.type(node.props)}
;(async()=>{
 let tree=parent(),selectedNode=selected(tree)
 assert.equal(selectedNode.props.rec.id,c.rid)
 assert.equal(selectedNode.props.rec.progressPct,0)
 const range=()=>nodes(detail(selectedNode)).find(n=>n.type==='input'&&n.props.type==='range')
 const note=()=>nodes(detail(selectedNode)).find(n=>n.props?.placeholder==='说明（未采纳必填）')
 range().props.onChange({target:{value:String(c.body.progressPct)}})
 note().props.onChange({target:{value:c.body.note}})
 await nodes(detail(selectedNode)).find(n=>n.type==='button'&&n.props.children==='保存进度').props.onClick()
 assert.equal(sent,1);assert.equal(boardReloads,1);assert.equal(auditReloads,1)
 // Keep real parent onChanged; rerender from the captured GET board, not PATCH substitution.
 tree=parent();selectedNode=selected(tree)
 assert.equal(selectedNode.props.rec.id,c.rid)
 assert.deepEqual(JSON.parse(JSON.stringify(selectedNode.props.rec)),c.returned)
 assert.equal(range().props.value,35);assert.equal(note().props.value,'')
 assert.equal(nodes(detail(selectedNode)).find(n=>n.type==='button'&&n.props.children==='保存进度').props.disabled,true)
 assert.equal(notices.at(-1)[1],'ok')
 const reportLink=nodes(tree).find(n=>n.type==='a'&&n.props.href?.startsWith('#/report?'))
 assert.equal(new URLSearchParams(reportLink.props.href.split('?')[1]).get('case'),c.case.caseId)
 console.log('captured board reload: requested recommendation, progress, parent refresh and case link passed')
})().catch(e=>{console.error(e);process.exitCode=1})

// Actual ReportPage callbacks, synthetic render/commit/API promises. No browser/backend.
// VM imports are allowlisted; no fetch is supplied. No permission/refusal cases.
const assert=require('node:assert/strict'),vm=require('node:vm'),{buildSync}=require('esbuild')
const parserBox={exports:{}};vm.runInNewContext(buildSync({entryPoints:['src/caseContext.ts'],bundle:true,platform:'node',format:'cjs',write:false}).outputFiles[0].text,{module:parserBox,exports:parserBox.exports,URLSearchParams})
const code=buildSync({entryPoints:['src/pages/ReportPage.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const viewCode=buildSync({entryPoints:['src/reports/ReportView.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const jsx=(type,props,key)=>({type,props,key}),View=()=>null,Dialog=()=>null
const nodes=n=>!n?[]:Array.isArray(n)?n.flatMap(nodes):typeof n==='object'?[n,...nodes(n.props?.children)]:[]
async function scenario(mode){
 let query=mode==='latest'?'case=SYNTHETIC':'case=SYNTHETIC&report=R1',role='synthetic',reportId='R1',sectionIds=['first','second'],reviewCalls=0
 let release,reject,exportCalls=0; const wait=()=>new Promise((resolve,fail)=>{release=resolve;reject=fail})
 let currentStore,index=0,effects=[],sessionKey,sessionProps,Session,parentStore=[],sessionStore=[]
 const react={useState:v=>{const a=currentStore,i=index++;if(!(i in a))a[i]=typeof v==='function'?v():v;return[a[i],v=>a[i]=typeof v==='function'?v(a[i]):v]},useRef:v=>{const a=currentStore,i=index++;if(!(i in a))a[i]={current:v};return a[i]},useMemo:f=>f(),useSyncExternalStore:(_,f)=>f(),useEffect:effect,useLayoutEffect:effect}
 function effect(f,deps){const a=currentStore,i=index++,old=a[i];if(!old||!deps||deps.some((v,j)=>!Object.is(v,old.deps?.[j]))){effects.push(()=>{old?.cleanup?.();a[i]={deps,cleanup:f()}})}}
 function commit(){for(const f of effects.splice(0))f()}
 function unmount(store){for(const item of store)item?.cleanup?.()}
 const document=()=>({reportId,caseId:new URLSearchParams(query).get('case'),templateId:'imo-cic',lang:'bilingual',createdUtc:'2026-01-01',version:1,sections:sectionIds.map(sectionId=>({sectionId,sentences:[],dataSources:[],status:'Draft'}))})
 const api={cases:async()=>[],templates:async()=>({templates:[]}),list:async()=>({reports:[document()],realDataStatus:'fictional'}),gisis:async()=>({fields:[]}),get:async()=>document(),audit:async()=>[],review:async(c,r,s)=>{reviewCalls++;await wait();return {sectionId:s,sentences:[],dataSources:[],status:'Modified'}},export:async()=>{exportCalls++;await wait();return {filename:'synthetic.pdf'}},gisisExport:async()=>{await wait()}}
 const modules={'../caseContext':parserBox.exports,react,'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[new URLSearchParams(query),()=>{}]},'../reports/api':{createReportApi:()=>api,ReportApiError:class extends Error{}},'../reports/ReportView':{ReportView:View,ReviewDialog:Dialog},'../api':{getRole:()=>role,getOperator:()=> 'synthetic',onIdentityChange:()=>()=>{}},'../cases/model':{parseCases:v=>v},'../reportOutput/Panel':{ReportOutputPanel:()=>null},'../archiveProvenance/Provenance':{ArchiveProvenance:()=>null},'../reports/types':{DEMO_CASE_ID:'SYNTHETIC'}}
 const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]},AbortController})
 const realViewBox={exports:{}}; const viewModules={react,'react/jsx-runtime':{jsx,jsxs:jsx},'../components/Panel':{Panel:()=>null},'../config':{SERVICE_ADDR:'synthetic'},'./types':{DEMO_CASE_ID:'SYNTHETIC'}}
 vm.runInNewContext(viewCode,{module:realViewBox,exports:realViewBox.exports,require:n=>{assert.ok(n in viewModules,n);return viewModules[n]}})
 function button(label){return nodes(realViewBox.exports.ReportView(view())).find(n=>n.type==='button'&&n.props.children===label)}
 function parent(){currentStore=parentStore;index=0;const element=box.exports.ReportPage();if(element.key!==sessionKey){unmount(sessionStore);sessionStore=[];sessionKey=element.key}sessionProps=element.props;Session=element.type}
 function tree(){currentStore=sessionStore;index=0;const result=Session(sessionProps);commit();return result}
 function view(){return nodes(tree()).find(n=>n.type===View).props}
 async function loaded(){parent();tree();commit();await new Promise(setImmediate);return view()}
 let v=await loaded(); assert.equal(v.busy,false)
 const oldExport=v.onExport
 oldExport('pdf');oldExport('pdf') // no render between actual parent callbacks
 assert.equal(exportCalls,1,'one export dispatch before saving rerenders')
 assert.equal(view().busy,true)
 view().onExport('pdf');assert.equal(exportCalls,1,'one dispatch while pending')
 if(mode==='case'){
   query='case=SYNTHETIC-OTHER&report=R1'; await loaded()
   assert.equal(view().busy,false)
   oldExport('pdf');assert.equal(exportCalls,1,'old context cannot dispatch')
   release();await new Promise(setImmediate)
   assert.equal(view().busy,false)
 } else {
   if(mode==='failure')reject(new Error('synthetic ordinary failure'));else release()
   await new Promise(setImmediate)
   v=view();assert.equal(v.busy,false)
   if(mode==='failure')assert.equal(v.error,'synthetic ordinary failure')
   else assert.ok(v.notice.includes('synthetic.pdf'))
   v.onExport('pdf');assert.equal(exportCalls,2,'explicit action permitted after settlement')
   release();await new Promise(setImmediate)
 }
}
let complete=false;process.on('beforeExit',()=>{if(!complete){console.error('FAIL: unfinished single-flight scenarios');process.exitCode=1}})
;(async()=>{for(const mode of ['success','failure','case'])await scenario(mode);complete=true;console.log('PASS report single-flight: 3 synthetic parent lifecycle scenarios')})().catch(e=>{console.error(e);process.exitCode=1})

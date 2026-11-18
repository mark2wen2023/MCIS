// Actual ReportPage + keyed ReportSession, synthetic lifecycle/API. No browser/backend.
const assert=require('node:assert/strict'),vm=require('node:vm'),{buildSync}=require('esbuild')
const code=buildSync({entryPoints:['src/pages/ReportPage.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const viewCode=buildSync({entryPoints:['src/reports/ReportView.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const jsx=(type,props,key)=>({type,props,key}),View=()=>null,Dialog=()=>null
const nodes=n=>!n?[]:Array.isArray(n)?n.flatMap(nodes):typeof n==='object'?[n,...nodes(n.props?.children)]:[]
async function scenario(mode){
 let query=mode==='latest'?'case=SYNTHETIC':'case=SYNTHETIC&report=R1',role='synthetic',reportId='R1',sectionIds=['first','second'],reviewCalls=0
 let release; const delayed=mode.startsWith('race-'); const wait=()=>delayed?new Promise(resolve=>{release=resolve}):Promise.resolve()
 let currentStore,index=0,effects=[],sessionKey,sessionProps,Session,parentStore=[],sessionStore=[]
 const react={useState:v=>{const a=currentStore,i=index++;if(!(i in a))a[i]=typeof v==='function'?v():v;return[a[i],v=>a[i]=typeof v==='function'?v(a[i]):v]},useRef:v=>{const a=currentStore,i=index++;if(!(i in a))a[i]={current:v};return a[i]},useMemo:f=>f(),useSyncExternalStore:(_,f)=>f(),useEffect:effect,useLayoutEffect:effect}
 function effect(f,deps){const a=currentStore,i=index++,old=a[i];if(!old||!deps||deps.some((v,j)=>!Object.is(v,old.deps?.[j]))){effects.push(()=>{old?.cleanup?.();a[i]={deps,cleanup:f()}})}}
 function commit(){for(const f of effects.splice(0))f()}
 function unmount(store){for(const item of store)item?.cleanup?.()}
 const document=()=>({reportId,caseId:new URLSearchParams(query).get('case'),templateId:'imo-cic',lang:'bilingual',createdUtc:'2026-01-01',version:1,sections:sectionIds.map(sectionId=>({sectionId,sentences:[],dataSources:[],status:'Draft'}))})
 const api={cases:async()=>[],templates:async()=>({templates:[]}),list:async()=>({reports:[document()],realDataStatus:'fictional'}),gisis:async()=>({fields:[]}),get:async()=>document(),audit:async()=>[],review:async(c,r,s)=>{reviewCalls++;await wait();return {sectionId:s,sentences:[],dataSources:[],status:'Modified'}},export:async()=>{await wait();return {filename:'synthetic.pdf'}},gisisExport:async()=>{await wait()}}
 const modules={react,'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[new URLSearchParams(query),()=>{}]},'../reports/api':{createReportApi:()=>api,ReportApiError:class extends Error{}},'../reports/ReportView':{ReportView:View,ReviewDialog:Dialog},'../api':{getRole:()=>role,getOperator:()=> 'synthetic',onIdentityChange:()=>()=>{}},'../cases/model':{parseCases:v=>v},'../reportOutput/Panel':{ReportOutputPanel:()=>null},'../archiveProvenance/Provenance':{ArchiveProvenance:()=>null},'../reports/types':{DEMO_CASE_ID:'SYNTHETIC'}}
 const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]},AbortController})
 const realViewBox={exports:{}}; const viewModules={react,'react/jsx-runtime':{jsx,jsxs:jsx},'../components/Panel':{Panel:()=>null},'../config':{SERVICE_ADDR:'synthetic'},'./types':{DEMO_CASE_ID:'SYNTHETIC'}}
 vm.runInNewContext(viewCode,{module:realViewBox,exports:realViewBox.exports,require:n=>{assert.ok(n in viewModules,n);return viewModules[n]}})
 function button(label){return nodes(realViewBox.exports.ReportView(view())).find(n=>n.type==='button'&&n.props.children===label)}
 function parent(){currentStore=parentStore;index=0;const element=box.exports.ReportPage();if(element.key!==sessionKey){unmount(sessionStore);sessionStore=[];sessionKey=element.key}sessionProps=element.props;Session=element.type}
 function tree(){currentStore=sessionStore;index=0;const result=Session(sessionProps);commit();return result}
 function view(){return nodes(tree()).find(n=>n.type===View).props}
 async function loaded(){parent();tree();commit();await new Promise(setImmediate);return view()}
 let v=await loaded();assert.equal(v.selectedSectionId,'first');v.onSelectSection('second');assert.equal(view().selectedSectionId,'second')
 const before=sessionKey
 let pending
 if(mode==='manual') {const b=button('刷新');assert.equal(b.props.disabled,false);b.props.onClick({type:'click',nativeEvent:{synthetic:true}})}
 else if(mode==='export'||mode==='race-export')view().onExport('pdf')
 else if(mode==='race-gisis')view().onGisisExport('json')
 else {view().onReview('modify',{sectionId:'second'});const d=nodes(tree()).find(n=>n.type===Dialog);pending=d.props.onSubmit({action:'modify',textZh:'synthetic',reason:'synthetic'})}
 if(delayed){
   assert.equal(view().busy,true)
   const chips=nodes(realViewBox.exports.ReportView(view())).filter(n=>n.type==='button'&&n.props.className?.includes('rpt-section-chip'))
   assert.ok(!chips[0].props.disabled);chips[0].props.onClick()
   assert.equal(view().selectedSectionId,'first')
   if(mode==='race-case'){query='case=SYNTHETIC-OTHER&report=R1';await loaded()}
   const activeKey=sessionKey;release();await pending;await new Promise(setImmediate)
   if(mode==='race-case'){parent();assert.equal(sessionKey,activeKey,'late old-case save cannot refresh new case')}
 } else {await pending;await new Promise(setImmediate)}
 if(mode==='missing')sectionIds=['first']
 if(mode==='case')query='case=SYNTHETIC-OTHER&report=R1'
 if(mode==='report'){query='case=SYNTHETIC&report=R2';reportId='R2'}
 if(mode==='latest')reportId='R2' // server chooses another report even without query change
 if(mode==='identity')role='synthetic-other'
 v=await loaded();assert.notEqual(sessionKey,before,'exercise actual keyed remount')
 assert.equal(v.selectedSectionId,['save','export','manual'].includes(mode)?'second':'first',mode)
 assert.equal(reviewCalls,['export','manual','race-export','race-gisis'].includes(mode)?0:1,'no duplicate mutation')
}
let complete=false;process.on('beforeExit',()=>{if(!complete){console.error('FAIL: report scenarios unfinished');process.exitCode=1}})
;(async()=>{for(const mode of (process.argv[2]?[process.argv[2]]:['save','export','missing','case','report','latest','identity','manual','race-save','race-export','race-gisis','race-case']))await scenario(mode);complete=true;console.log('report section refresh: selected synthetic lifecycle scenarios passed (full selection: 12)')})().catch(e=>{console.error(e);process.exitCode=1})

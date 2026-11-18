// Actual ReportPage + keyed ReportSession, synthetic lifecycle/API. No browser/backend.
const assert=require('node:assert/strict'),vm=require('node:vm'),{buildSync}=require('esbuild')
const code=buildSync({entryPoints:['src/pages/ReportPage.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const jsx=(type,props,key)=>({type,props,key}),View=()=>null,Dialog=()=>null
const nodes=n=>!n?[]:Array.isArray(n)?n.flatMap(nodes):typeof n==='object'?[n,...nodes(n.props?.children)]:[]
async function scenario(mode){
 let query=mode==='latest'?'case=SYNTHETIC':'case=SYNTHETIC&report=R1',role='synthetic',reportId='R1',sectionIds=['first','second'],reviewCalls=0
 let currentStore,index=0,effects=[],cleanups=[],sessionKey,sessionProps,Session,parentStore=[],sessionStore=[]
 const react={useState:v=>{const a=currentStore,i=index++;if(!(i in a))a[i]=typeof v==='function'?v():v;return[a[i],v=>a[i]=typeof v==='function'?v(a[i]):v]},useRef:v=>{const a=currentStore,i=index++;if(!(i in a))a[i]={current:v};return a[i]},useMemo:f=>f(),useSyncExternalStore:(_,f)=>f(),useEffect:effect,useLayoutEffect:effect}
 function effect(f){const a=currentStore,i=index++;if(!(i in a)){a[i]=true;effects.push(f)}}
 const document=()=>({reportId,caseId:new URLSearchParams(query).get('case'),templateId:'imo-cic',lang:'bilingual',createdUtc:'2026-01-01',version:1,sections:sectionIds.map(sectionId=>({sectionId,sentences:[]}))})
 const api={cases:async()=>[],templates:async()=>({templates:[]}),list:async()=>({reports:[document()],realDataStatus:'fictional'}),gisis:async()=>({fields:[]}),get:async()=>document(),audit:async()=>[],review:async(c,r,s)=>{reviewCalls++;return {sectionId:s,sentences:[]}},export:async()=>({filename:'synthetic.pdf'}),gisisExport:async()=>{}}
 const modules={react,'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[new URLSearchParams(query),()=>{}]},'../reports/api':{createReportApi:()=>api,ReportApiError:class extends Error{}},'../reports/ReportView':{ReportView:View,ReviewDialog:Dialog},'../api':{getRole:()=>role,getOperator:()=> 'synthetic',onIdentityChange:()=>()=>{}},'../cases/model':{parseCases:v=>v},'../reportOutput/Panel':{ReportOutputPanel:()=>null},'../archiveProvenance/Provenance':{ArchiveProvenance:()=>null},'../reports/types':{DEMO_CASE_ID:'SYNTHETIC'}}
 const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]},AbortController})
 function parent(){currentStore=parentStore;index=0;const element=box.exports.ReportPage();if(element.key!==sessionKey){for(const f of cleanups)f();cleanups=[];sessionStore=[];sessionKey=element.key}sessionProps=element.props;Session=element.type}
 function tree(){currentStore=sessionStore;index=0;return Session(sessionProps)}
 function view(){return nodes(tree()).find(n=>n.type===View).props}
 async function loaded(){parent();tree();for(const f of effects.splice(0)){const clean=f();if(clean)cleanups.push(clean)}await new Promise(setImmediate);return view()}
 let v=await loaded();assert.equal(v.selectedSectionId,'first');v.onSelectSection('second');assert.equal(view().selectedSectionId,'second')
 const before=sessionKey
 if(mode==='export') {view().onExport('pdf');await new Promise(setImmediate)}
 else {view().onReview('modify',{sectionId:'second'});const d=nodes(tree()).find(n=>n.type===Dialog);await d.props.onSubmit({action:'modify',textZh:'synthetic',reason:'synthetic'})}
 if(mode==='missing')sectionIds=['first']
 if(mode==='case')query='case=SYNTHETIC-OTHER&report=R1'
 if(mode==='report'){query='case=SYNTHETIC&report=R2';reportId='R2'}
 if(mode==='latest')reportId='R2' // server chooses another report even without query change
 if(mode==='identity')role='synthetic-other'
 v=await loaded();assert.notEqual(sessionKey,before,'exercise actual keyed remount')
 assert.equal(v.selectedSectionId,['save','export'].includes(mode)?'second':'first',mode)
 assert.equal(reviewCalls,mode==='export'?0:1,'no duplicate mutation')
}
;(async()=>{for(const mode of ['save','export','missing','case','report','latest','identity'])await scenario(mode);console.log('report section refresh: 7 synthetic lifecycle scenarios passed')})().catch(e=>{console.error(e);process.exitCode=1})

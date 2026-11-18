// Actual ReportSession callbacks; synthetic hooks, deferred API and no startup effects.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),{buildSync}=require('esbuild')
const source=fs.readFileSync('src/pages/ReportPage.tsx','utf8')+'\nexport { ReportSession };'
const code=buildSync({stdin:{contents:source,sourcefile:'ReportPage.tsx',loader:'tsx'},bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const jsx=(type,props,key)=>({type,props,key}),View=()=>null
const nodes=n=>!n?[]:Array.isArray(n)?n.flatMap(nodes):typeof n==='object'?[n,...nodes(n.props?.children)]:[]
async function scenario(exportFile,changed){
 let index=0;const state=[],requests=[]
 const api={gisisValidate:(c,v)=>new Promise(resolve=>requests.push({c,v,resolve})),gisisValidateExport:(c,v)=>new Promise(resolve=>requests.push({c,v,resolve}))}
 const modules={react:{useState:v=>{const i=index++;if(!(i in state))state[i]=v;return[state[i],v=>state[i]=typeof v==='function'?v(state[i]):v]},useRef:v=>{const i=index++;if(!(i in state))state[i]={current:v};return state[i]},useMemo:f=>f(),useEffect:()=>{},useLayoutEffect:()=>{}},'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[new URLSearchParams('case=SYNTHETIC'),()=>{}]},'../reports/api':{createReportApi:()=>api,ReportApiError:class extends Error{}},'../reports/ReportView':{ReportView:View,ReviewDialog:()=>null},'../api':{getRole:()=> 'synthetic',getOperator:()=> 'synthetic',onIdentityChange:()=>()=>{}},'../cases/model':{parseCases:v=>v},'../reportOutput/Panel':{ReportOutputPanel:()=>null},'../archiveProvenance/Provenance':{ArchiveProvenance:()=>null},'../reports/types':{DEMO_CASE_ID:'SYNTHETIC'}}
 const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}})
 const render=()=>{index=0;return nodes(box.exports.ReportSession({identity:'["synthetic","synthetic"]',isActive:()=>true,refresh:()=>{}})).find(n=>n.type===View).props}
 render().onGisisValidate({field:'A'},exportFile)
 if(changed)render().onGisisEdit?.() // queued input before parent busy render is consumed
 requests[0].resolve({valid:true,errors:[],fields:[]});await new Promise(setImmediate)
 const result=render()
 if(changed){assert.equal(result.validation,null,'late result must not certify changed input');assert.ok(!result.notice?.includes('校验通过'));assert.match(result.notice,/输入已变化/)}
 else if(exportFile){assert.match(result.notice,/校验通过并已导出/)}
 else {assert.equal(result.validation.valid,true)}
 result.onGisisEdit?.()
 assert.equal(render().validation,null,'editing clears previous result')
 assert.ok(!render().notice?.includes('校验通过') && !render().notice?.includes('输入已变化'),'editing clears previous result notice; startup loading message may remain in this harness')
 assert.equal(requests.length,1,'no automatic retry')
}
;(async()=>{for(const exp of [false,true])for(const changed of [true,false])await scenario(exp,changed);console.log('GISIS parent: 4 synthetic deferred callback flows passed')})().catch(e=>{console.error(e);process.exitCode=1})

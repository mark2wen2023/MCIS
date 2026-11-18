// Consumes only the synthetic TestClient capture on stdin. Replays actual returned
// bytes into ReportSession; no HTTP, fake success body, browser or denied request.
const fs=require('node:fs'),assert=require('node:assert/strict'),vm=require('node:vm')
const {buildSync}=require('esbuild'),React=require('react'),{renderToStaticMarkup}=require('react-dom/server')
const capture=JSON.parse(fs.readFileSync(0,'utf8'))
const source=fs.readFileSync('src/pages/ReportPage.tsx','utf8')+'\nexport { ReportSession };'
const code=buildSync({stdin:{contents:source,sourcefile:'ReportPage.tsx',loader:'tsx'},bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
let index=0,effectIndex=0,refreshes=0;const state=[],effects=[],queue=[],sent=[]
const jsx=(type,props,key)=>({type,props,key}),View=()=>null,Dialog=()=>null
const nodes=n=>!n?[]:Array.isArray(n)?n.flatMap(nodes):typeof n==='object'?[n,...nodes(n.props?.children)]:[]
const api={cases:async()=>[capture.case],templates:async()=>({templates:[]}),list:async()=>({reports:[capture.initial],realDataStatus:'fictional'}),gisis:async()=>({fields:[]}),get:async()=>capture.initial,audit:async()=>[],review:async(c,r,s,body)=>{sent.push({c,r,s,body});assert.deepEqual(JSON.parse(JSON.stringify(body)),capture.body);return capture.returned}}
const react={useState:v=>{const n=index++;if(!(n in state))state[n]=v;return[state[n],v=>state[n]=typeof v==='function'?v(state[n]):v]},useRef:v=>{const n=index++;if(!(n in state))state[n]={current:v};return state[n]},useMemo:f=>f(),useEffect:(fn)=>{const n=effectIndex++;if(!effects[n]){effects[n]=true;queue.push(fn)}},useLayoutEffect:()=>{}}
const modules={react,'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{useSearchParams:()=>[new URLSearchParams({case:capture.case.caseId,report:capture.initial.reportId}),()=>{}]},'../reports/api':{createReportApi:()=>api,ReportApiError:class extends Error{}},'../reports/ReportView':{ReportView:View,ReviewDialog:Dialog},'../api':{getRole:()=> 'LeadInvestigator',getOperator:()=> 'Synthetic reviewer',onIdentityChange:()=>()=>{}},'../cases/model':{parseCases:v=>v},'../reportOutput/Panel':{ReportOutputPanel:()=>null},'../archiveProvenance/Provenance':{ArchiveProvenance:()=>null},'../reports/types':{DEMO_CASE_ID:'SYNTHETIC'}}
const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]},AbortController})
function render(){index=0;effectIndex=0;return nodes(box.exports.ReportSession({identity:'["LeadInvestigator","Synthetic reviewer"]',isActive:()=>true,refresh:()=>refreshes++}))}
;(async()=>{
 render();queue.splice(0).forEach(f=>f());await new Promise(setImmediate)
 let view=render().find(n=>n.type===View).props
 assert.equal(view.report.sections[0].sentences[0].source,'Generated')
 view.onReview('modify',{sectionId:'analysis',sentenceId:'SYNTHETIC-S',title:'Synthetic',textZh:'original',textEn:'original'})
 const dialog=render().find(n=>n.type===Dialog);assert.ok(dialog)
 await dialog.props.onSubmit(capture.body)
 const tree=render();view=tree.find(n=>n.type===View).props
 assert.equal(sent.length,1);assert.equal(sent[0].c,capture.case.caseId);assert.equal(sent[0].r,capture.initial.reportId);assert.equal(sent[0].s,'analysis')
 assert.deepEqual(view.report.sections[0],capture.returned)
 assert.equal(tree.some(n=>n.type===Dialog),false);assert.equal(refreshes,1)
 assert.ok(view.notice.includes('复核已保存'))
 // Render the actual view with the parent's resulting props, not the placeholder.
 const actualCode=buildSync({entryPoints:['src/reports/ReportView.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['react','react/jsx-runtime'],write:false}).outputFiles[0].text
 const actual={exports:{}};vm.runInNewContext(actualCode,{module:actual,exports:actual.exports,require})
 const html=renderToStaticMarkup(React.createElement(actual.exports.ReportView,view))
 assert.ok(html.includes('来源 Investigator'));assert.ok(html.includes(capture.body.textZh))
 assert.ok(html.includes('引用沿用原生成内容'));assert.ok(html.includes('SYNTHETIC-E'))
 const sentence=view.report.sections[0].sentences[0]
 assert.deepEqual(sentence.generatedText,capture.initial.sections[0].sentences[0].generatedText)
 assert.deepEqual(sentence.reviews,capture.saved.sections[0].sentences[0].reviews)
 console.log('Normal parent callback + SSR accepted captured service response; no browser/full remount claim')
})().catch(e=>{console.error(e);process.exitCode=1})

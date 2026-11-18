// Actual component functions with controlled commit/discard hooks; not React scheduling.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const {buildSync}=require('../../web/node_modules/esbuild');
globalThis.fetch=()=>{throw Error('network forbidden')};
const jsx=(type,props,key)=>({type,props,key});
const compile=(path,extra='')=>buildSync({stdin:{contents:fs.readFileSync(path,'utf8')+extra,resolveDir:process.cwd(),loader:'tsx'},bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text;
function harness(){let cells=[],index=0,pending=[];const hooks={useRef(v){const i=index++;return cells[i]??(cells[i]={current:v})},useState(v){const i=index++;if(!(i in cells))cells[i]=typeof v==='function'?v():v;return[cells[i],n=>cells[i]=typeof n==='function'?n(cells[i]):n]},useSyncExternalStore:(_,f)=>f(),useMemo:f=>f(),useCallback:f=>f()};
 function effect(f,deps){const i=index++,old=cells[i];if(!old||!deps||deps.some((d,j)=>d!==old.deps[j]))pending.push(()=>{old?.cleanup?.();cells[i]={deps,cleanup:f()}})}
 hooks.useLayoutEffect=effect;hooks.useEffect=effect;
 return {hooks,render(f){index=0;pending=[];return f()},commit(){const list=pending;pending=[];list.forEach(f=>f())},discard(){pending=[]},unmount(){cells.forEach(c=>c?.cleanup?.())}};
}
function load(code,mods){const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in mods,n);return mods[n]},AbortController});return box.exports}
const nodes=n=>!n?[]:Array.isArray(n)?n.flatMap(nodes):typeof n==='object'?[n,...nodes(n.props?.children)]:[];
const runtime=h=>({react:h.hooks,'react/jsx-runtime':{jsx,jsxs:jsx}});
{
 const h=harness();let query='case=A',identity='synthetic';
 const mods={...runtime(h),'react-router-dom':{useSearchParams:()=>[new URLSearchParams(query)]},'../api':{getRole:()=>identity,getOperator:()=> 'op',onIdentityChange:()=>()=>{}},'../reports/api':{},'../reports/ReportView':{},'../cases/model':{},'../reportOutput/Panel':{},'../archiveProvenance/Provenance':{},'../reports/types':{}};
 const {ReportPage}=load(compile('web/src/pages/ReportPage.tsx'),mods);
 const render=()=>h.render(ReportPage);
 let a=render();assert.equal(a.props.isActive(),false);h.commit();assert.equal(a.props.isActive(),true);
 a.props.refresh({reportId:'R-A',sectionId:'second'});a=render();h.commit();assert.equal(a.props.initialSelection.sectionId,'second');
 query='case=B';const abandoned=render();assert.equal(abandoned.props.initialSelection,undefined);assert.equal(abandoned.props.isActive(),false);assert.equal(a.props.isActive(),true);h.discard();
 query='case=A';const retained=render();assert.equal(retained.props.initialSelection.sectionId,'second');h.commit();
 query='case=B';let b=render();h.commit();assert.equal(a.props.isActive(),false);assert.equal(b.props.isActive(),true);a.props.refresh({reportId:'BAD',sectionId:'bad'});b=render();assert.equal(b.props.initialSelection,undefined);h.commit();
 identity='changed';assert.equal(b.props.isActive(),false);h.unmount();assert.equal(b.props.isActive(),false);
}
{
 const h=harness(),sent=[];let active=true;
 const api={patch:(...args)=>{sent.push(args);return new Promise(()=>{})},post:()=>{throw Error('unexpected post')}};
 const mods={...runtime(h),'react-router-dom':{},'../api':{api,ApiError:class extends Error{},casePath:(p,c)=>c+p,getRole:()=> 'role',getOperator:()=> 'op'},'../components/Toast':{useToast:()=>()=>{}},'../components/Panel':{},'../config':{},'../recommendationReview/RecommendationReview':{},'../consultation/ConsultationPanel':{},'../format':{toLocal:v=>v,daysUntil:()=>0},'../recommendationReview/useBoardLoad':{}};
 const {TestDetail}=load(compile('web/src/pages/RecommendationsPage.tsx','\nexport { Detail as TestDetail };'),mods);
 let props={caseId:'SYNTH',readReady:true,readCurrent:()=>active,rec:{id:'REC',progressPct:25,status:'Responded',addressee:'synthetic',responses:[],history:[],causeNodeIds:[],evidenceIds:[]},allowed:[],pending:null,onChanged(){},onCancel(){}};
 const render=()=>h.render(()=>TestDetail(props));let tree=render();h.commit();
 const input=t=>nodes(t).find(n=>n.type==='input'&&n.props.placeholder==='说明（未采纳必填）');
 input(tree).props.onChange({target:{value:'keep draft'}});tree=render();h.commit();
 props={...props,rec:{...props.rec,progressPct:50}};tree=render();h.commit();
 const adopt=nodes(tree).find(n=>n.type==='button'&&n.props.children==='采用当前已读取进度，保留说明').props.onClick;
 props={...props,rec:{...props.rec,progressPct:60}};render();h.discard();
 // Abandoned 60 must not invalidate the committed 50 callback.
 adopt();props={...props,rec:{...props.rec,progressPct:50}};tree=render();h.commit();assert.equal(nodes(tree).find(n=>n.props?.type==='range').props.value,50);assert.equal(input(tree).props.value,'keep draft');
 props={...props,rec:{...props.rec,progressPct:60}};tree=render();h.commit();adopt();tree=render();h.commit();assert.equal(nodes(tree).find(n=>n.props?.type==='range').props.value,50);
 active=false;const currentAdopt=nodes(tree).find(n=>n.type==='button'&&n.props.children==='采用当前已读取进度，保留说明').props.onClick;currentAdopt();assert.equal(sent.length,0);assert.equal(input(render()).props.value,'keep draft');
}
(async()=>{
 const h=harness(),calls=[];
 const mods={...runtime(h),'../api':{ApiError:class extends Error{},getRole:()=> 'role',getOperator:()=> 'op'}};
 const {useLoad}=load(compile('web/src/recommendationReview/useBoardLoad.ts'),mods);
 const a=()=>{calls.push('A');return Promise.resolve('A')},b=()=>{calls.push('B');return Promise.resolve('B')};
 let view=h.render(()=>useLoad(a));h.commit();await Promise.resolve();view=h.render(()=>useLoad(a));h.commit();view.reload();h.render(()=>useLoad(b));h.discard();h.render(()=>useLoad(a));h.commit();await Promise.resolve();assert.deepEqual(calls,['A','A']);
 console.log('PASS report context/selection, Detail committed source/draft, board discarded-loader synthetic cases; not real React/browser');
})().catch(e=>{console.error(e);process.exitCode=1});

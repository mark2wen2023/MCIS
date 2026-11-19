const assert=require('node:assert/strict'),vm=require('node:vm'),{buildSync}=require('esbuild')
const compile=p=>buildSync({entryPoints:[p],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const load=(p,modules)=>{const m={exports:{}};vm.runInNewContext(compile(p),{module:m,exports:m.exports,URLSearchParams,AbortController,require:n=>{assert.ok(n in modules,n);return modules[n]},fetch:()=>{throw Error('network forbidden')}});return m.exports}
const parser=load('src/caseContext.ts',{}),jsx=(type,props,key)=>({type,props,key}),nodes=n=>!n?[]:Array.isArray(n)?n.flatMap(nodes):typeof n==='object'?[n,...nodes(n.props?.children)]:[]
let pathname='/report',query='',s,index,effects=[],reads=[],role='synthetic'
const effect=(f,deps)=>{const a=s,i=index++,old=a[i];if(!old||deps.some((v,j)=>v!==old.deps[j]))effects.push(()=>{old?.cleanup?.();a[i]={deps,cleanup:f()}})}
const react={useState:v=>{const a=s,i=index++;if(!(i in a))a[i]=typeof v==='function'?v():v;return[a[i],v=>a[i]=typeof v==='function'?v(a[i]):v]},useRef:v=>{const a=s,i=index++;return a[i]??(a[i]={current:v})},useMemo:f=>f(),useEffect:effect,useLayoutEffect:effect,useSyncExternalStore:(_,f)=>f()}
const Link=()=>null,Outlet=()=>null
const common={react,'react/jsx-runtime':{jsx,jsxs:jsx},'react-router-dom':{Link,NavLink:Link,Outlet,useLocation:()=>({pathname,search:query}),useSearchParams:()=>[new URLSearchParams(query),()=>{throw Error('unexpected query change')} ]}}
const identity={getRole:()=>role,getOperator:()=> 'synthetic',onIdentityChange:()=>()=>{},setIdentity:()=>{},CASE_ID:'SYN-DEMO',api:{get:p=>{reads.push(p);return Promise.resolve({caseId:parser.explicitCaseId(query),title:'SYN TITLE'})}}}
const api=new Proxy({},{get:(_,name)=>(...args)=>{reads.push([name,...args.filter(x=>typeof x==='string')]);return Promise.resolve(name==='cases'?[]:name==='templates'?{templates:[]}:name==='list'?{reports:[]}:name==='gisis'?{fields:[]}:name==='get'?{sections:[],reportId:args[1]}:[])}})
const Report=load('src/pages/ReportPage.tsx',{...common,'../caseContext':parser,'../api':identity,'../reports/api':{createReportApi:()=>api,ReportApiError:class extends Error{}},'../reports/ReportView':{ReportView:()=>null,ReviewDialog:()=>null},'../cases/model':{parseCases:x=>x},'../reportOutput/Panel':{ReportOutputPanel:()=>null},'../archiveProvenance/Provenance':{ArchiveProvenance:()=>null},'../reports/types':{DEMO_CASE_ID:'SYN-DEMO'}}).ReportPage
const Layout=load('src/Layout.tsx',{...common,'./api':identity,'./caseContext':parser,'./caseMetadata/events':{onCaseMetadataChanged:()=>()=>{}},'./routes':{ROUTES:[{path:'report',group:'core',name:'报告'},{path:'lobby',group:'core',name:'大厅'}]},'./components/CaseLoadStatus':{CaseLoadStatus:()=>null},'./caseFlow/CaseWorkspaceFlow':{CaseWorkspaceFlow:()=>null},'./config':{SERVICE_ADDR:'synthetic'}}).Layout
const parent=[],shell=[];let session=[],key
function render(fn,store,props){s=store;index=0;return fn(props)}
function commit(){for(const f of effects.splice(0))f()}
async function visit(q,valid){query=q;reads=[];let l=render(Layout,shell),r=render(Report,parent);commit()
 assert.equal(nodes(l).some(n=>n.type===Outlet),valid)
 if(key!==r.key){for(const x of session)x?.cleanup?.();session=[];key=r.key}
 if(valid){render(r.type,session,r.props);commit();await new Promise(setImmediate);assert.ok(reads.some(x=>typeof x==='string'&&x.endsWith(encodeURIComponent(parser.explicitCaseId(q)))));assert.ok(reads.some(x=>Array.isArray(x)&&x[0]==='list'&&x[1]===parser.explicitCaseId(q)))}
 else {await new Promise(setImmediate);assert.equal(reads.length,0);assert.ok(nodes(r).some(n=>n.type===Link&&n.props.to==='/lobby'));l=render(Layout,shell);commit();assert.ok(JSON.stringify(l).includes('请选择案件'));assert.ok(!JSON.stringify(l).includes('SYN TITLE'))}
 const navItems=nodes(l).filter(n=>typeof n.type==='function'&&n.props?.path)
 for(const item of navItems){const link=item.type(item.props);if(!valid)assert.equal(link.props.to,'/lobby');else if(item.props.path==='report')assert.equal(link.props.to,'/report?case='+encodeURIComponent(parser.explicitCaseId(q)))}
 assert.equal(query,q)
}
let done=false;process.on('beforeExit',()=>{if(!done)process.exitCode=1})
;(async()=>{for(const q of ['', '?case=', '?case=%20', '?case=A&case=A','?case=A&case=B','?case=%20A'])await visit(q,false)
 await visit('?case=SYN%20%2F%3F%26%E8%88%B9&report=OLD&template=imo-cic&lang=zh',true)
 assert.ok(reads.some(x=>Array.isArray(x)&&x[0]==='get'&&x[2]==='OLD'))
 await visit('?case=A&case=A',false);role='other';await visit('?case=SYN-B',true);await visit('?case=SYN-DEMO',true);await visit('',false)
 pathname='/lobby';query='';reads=[];const lobby=render(Layout,shell);commit();await new Promise(setImmediate);assert.equal(reads.length,0);assert.ok(nodes(lobby).some(n=>n.type===Outlet))
 done=true;console.log('PASS explicit-case actual Layout/ReportPage controlled hooks: invalid no reads, encoded history, explicit demo, transitions')})().catch(e=>{console.error(e);process.exitCode=1})

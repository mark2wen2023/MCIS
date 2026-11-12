import { renderToStaticMarkup } from 'react-dom/server'
import { parsePackageCheck, packageFileError, packageFilename, canUsePackages, MAX_PACKAGE_BYTES } from '../src/packages/model'
let n=0
function check(v: unknown, label: string) { if(!v) throw Error(label); n++ }
const good={isValid:true,tamperedFiles:[],missingFiles:[],extraFiles:[]}
check(parsePackageCheck(good).isValid,'valid')
check(!parsePackageCheck({...good,isValid:false,missingFiles:['case.json']}).isValid,'missing')
check(!parsePackageCheck({...good,isValid:false,tamperedFiles:['case.json']}).isValid,'tampered')
check(parsePackageCheck({...good,extraFiles:['not-listed']}).isValid,'extras informational')
for(const bad of [null,[],{}, {...good,isValid:'true'}, {...good,tamperedFiles:null}, {...good,missingFiles:[1]}, {...good,extraFiles:[{}]}, {...good,caseId:42}, {...good,packageFormat:false}, {...good,isValid:false}, {...good,tamperedFiles:['a']}, {...good,missingFiles:['b']}]) { let rejected=false;try{parsePackageCheck(bad)}catch{rejected=true}check(rejected,'malformed rejected') }
for(const role of ['Investigator','LeadInvestigator'])check(canUsePackages(role),'allowed')
for(const role of ['Public','AgentService','ExternalExpert','InterestedState','','Admin'])check(!canUsePackages(role),'closed role')
check(packageFileError({name:'x.MCASE',size:1})===null,'extension case')
check(packageFileError({name:'x.mcase',size:MAX_PACKAGE_BYTES})===null,'limit inclusive')
for(const file of [{name:'a.zip',size:1},{name:'a.mcase.exe',size:1},{name:'a.mcase',size:0},{name:'a.mcase',size:MAX_PACKAGE_BYTES+1}])check(!!packageFileError(file),'invalid file')
check(packageFilename('case/x?y')==='case_x_y.mcase','safe filename')
check(packageFilename('')==='case.mcase','empty safe')
async function main(){
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
const {PackageResult,PackagePanel,PackageExport}=await import('../src/packages/PackagePanel')
const html=renderToStaticMarkup(<PackageResult result={{...good,caseId:'<script>bad</script>',extraFiles:['<img src=x>']}}/>)
check(!html.includes('<script>')&&!html.includes('<img '),'escape result')
for(const term of ['清单哈希检查通过','本次没有导入案件','清单外文件','未被清单哈希覆盖','不代表来源真实'])check(html.includes(term),term)
check(renderToStaticMarkup(<PackageResult result={{...good,isValid:false,missingFiles:['manifest.json']}}/>).includes('清单哈希检查未通过'),'failure rendered')
const who='Investigator\n调查员 A'
const panel=renderToStaticMarkup(<PackagePanel who={who}/>);check(panel.includes('aria-expanded="false"')&&!panel.includes('type="file"'),'initially closed')
check(renderToStaticMarkup(<PackageExport caseId="x" title="标题" who={who}/>).includes('导出案件包：标题'),'labeled export')
const api=await import('../src/packages/api');const identity=await import('../src/api')
let calls:any[]=[]
globalThis.fetch=async (url,options)=>{calls.push({url,options});return new Response(JSON.stringify(good),{headers:{'Content-Type':'application/json'}})}
const file=new File(['zip'],'test.mcase')
await api.verifyPackage(file,who,new AbortController().signal)
check(calls[0].url==='/api/v1/packages:verify','real route')
check(calls[0].options.body===file&&calls[0].options.method==='POST','raw binary upload')
check(calls[0].options.headers['X-MCIS-Role']==='Investigator','role sent')
globalThis.fetch=async(url,options)=>{calls.push({url,options});return new Response('zip',{headers:{'Content-Type':'application/zip'}})}
check((await api.exportPackage('a /?#',who,new AbortController().signal)).size===3,'export blob')
check(calls.at(-1).url==='/api/v1/cases/a%20%2F%3F%23/export','encoded case')
for(const response of [new Response('{}',{headers:{'Content-Type':'application/json'}}),new Response('',{headers:{'Content-Type':'application/zip'}}),new Response('{"code":"FORBIDDEN","message":"private path"}',{status:403})]){globalThis.fetch=async()=>response;let error:unknown;try{await api.exportPackage('a',who,new AbortController().signal)}catch(e){error=e}check(!!error,'invalid download rejected');check(!api.packageError(error).includes('private path'),'no raw free-text errors')}
identity.setIdentity('Public');const before=calls.length;let denied=false;try{await api.exportPackage('a',who,new AbortController().signal)}catch{denied=true}check(denied&&calls.length===before,'identity and permission fail before fetch')
console.log(`W8.3 ${n} assertions passed`)
}
main().catch(error=>{console.error(error);process.exitCode=1})

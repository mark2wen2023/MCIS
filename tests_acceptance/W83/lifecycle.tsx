import assert from 'node:assert/strict'
import {PackagePanel,PackageExport,PackageResult} from '../../web/src/packages/PackagePanel'
import {instance,render,unmount} from './hooks'
import {setIdentity} from './identity'
const listeners=new Map<string,Set<any>>()
const win={addEventListener:(k:string,f:any)=>{if(!listeners.has(k))listeners.set(k,new Set());listeners.get(k)!.add(f)},removeEventListener:(k:string,f:any)=>listeners.get(k)?.delete(f),setTimeout:(f:any)=>{f();return 1},location:{href:'http://localhost/#/lobby',origin:'http://localhost',pathname:'/',search:'',hash:'#/lobby'}}
globalThis.window=win as any
const navigate=()=>{for(const f of [...(listeners.get('popstate')||[])])f()}
const WHO='Investigator\n独立验收';let count=0
function ck(name:string,v:any){assert.ok(v,name);count++;console.log('PASS '+name)}
function nodes(el:any):any[]{return !el||typeof el!=='object'?[]:[el,...[el.props?.children].flat(Infinity).flatMap(nodes)]}
const button=(el:any,label:string)=>nodes(el).find(n=>n.type==='button'&&n.props.children===label)
let pending:any[]=[];let requests:any[]=[]
globalThis.fetch=((url:any,options:any)=>{requests.push({url,options});return new Promise((resolve,reject)=>pending.push({resolve,reject}))}) as any
const tick=async()=>{for(let i=0;i<10;i++)await Promise.resolve()}
const valid={isValid:true,missingFiles:[],tamperedFiles:[],extraFiles:[],caseId:'CASE-QA'}
function form(){const p=instance();let panel=render(p,()=>PackagePanel({who:WHO}));button(panel,'选择案件包预检').props.onClick();panel=render(p,()=>PackagePanel({who:WHO}));const child=nodes(panel).find(n=>typeof n.type==='function');const i=instance();const view=()=>render(i,()=>child.type(child.props));return {i,view}}
function choose(v:any,file:File){nodes(v).find(n=>n.type==='input').props.onChange({target:{files:[file]}})}
async function checks(){
 const file=new File(['zip'],'qa.mcase')
 let f=form();choose(f.view(),file);ck('select does not upload',requests.length===0)
 let v=f.view();button(v,'上传并预检').props.onClick();button(v,'上传并预检').props.onClick();ck('same-render double click sends once',requests.length===1)
 ck('inflight disabled',button(f.view(),'正在预检…').props.disabled)
 choose(f.view(),new File(['new'],'new.mcase'));ck('file replacement aborts old request',requests[0].options.signal.aborted)
 pending.shift().resolve(Response.json(valid));await tick();ck('late old file response hidden',!nodes(f.view()).some(n=>n.type===PackageResult))
 button(f.view(),'上传并预检').props.onClick();pending.shift().resolve(Response.json(valid));await tick();ck('new file response appears',nodes(f.view()).some(n=>n.type===PackageResult))
 button(f.view(),'上传并预检').props.onClick();ck('new run clears prior report',!nodes(f.view()).some(n=>n.type===PackageResult));button(f.view(),'停止等待').props.onClick();pending.shift().resolve(Response.json(valid));await tick();ck('cancel suppresses late response',!nodes(f.view()).some(n=>n.type===PackageResult))
 button(f.view(),'上传并预检').props.onClick();unmount(f.i);ck('close/unmount aborts request',requests.at(-1).options.signal.aborted);pending.shift().resolve(Response.json(valid));await tick()
 f=form();choose(f.view(),file);button(f.view(),'上传并预检').props.onClick();setIdentity('Public');ck('identity change aborts',requests.at(-1).options.signal.aborted);pending.shift().resolve(Response.json(valid));await tick();ck('identity late response hidden',!nodes(f.view()).some(n=>n.type===PackageResult));unmount(f.i);setIdentity('Investigator')
 f=form();choose(f.view(),new File([],'empty.mcase'));ck('empty upload disabled',button(f.view(),'上传并预检').props.disabled);choose(f.view(),new File(['x'],'bad.txt'));ck('non-mcase disabled',button(f.view(),'上传并预检').props.disabled);unmount(f.i)
 for(const response of [Response.json({...valid,isValid:false}),Response.json({isValid:true}),new Response('bad',{status:500}),Response.json({code:'FORBIDDEN'},{status:403}),Response.json({code:'BAD_PACKAGE'},{status:422})]){
  f=form();choose(f.view(),file);button(f.view(),'上传并预检').props.onClick();pending.shift().resolve(response);await tick();ck('invalid/error response no success',!nodes(f.view()).some(n=>n.type===PackageResult)&&nodes(f.view()).some(n=>n.props?.role==='alert'));unmount(f.i)
 }
 let downloads=0,created=0,revoked=0
 globalThis.document={createElement:()=>({click(){downloads++},remove(){},href:'',download:''}),body:{appendChild(){}}} as any
 globalThis.window=win as any
 URL.createObjectURL=()=>{created++;return 'blob:test'};URL.revokeObjectURL=()=>{revoked++}
 let i=instance();let view=()=>render(i,()=>PackageExport({caseId:'case 空格?#',title:'测试',who:WHO}))
 const run=button(view(),'导出 .mcase').props.onClick;const before=requests.length;run();run();ck('export double click sends once',requests.length===before+1);ck('case path percent encoded',requests.at(-1).url==='/api/v1/cases/case%20%E7%A9%BA%E6%A0%BC%3F%23/export')
 pending.shift().resolve(new Response('zip',{headers:{'Content-Type':'application/zip'}}));await tick();ck('success hands download once',downloads===1&&created===1&&revoked===1)
 button(view(),'导出 .mcase').props.onClick();setIdentity('Public');pending.shift().resolve(new Response('zip',{headers:{'Content-Type':'application/zip'}}));await tick();ck('late identity export cannot download',downloads===1);unmount(i);setIdentity('Investigator')
 for(const r of [new Response('html',{headers:{'Content-Type':'text/html'}}),new Response('',{headers:{'Content-Type':'application/zip'}}),new Response('error',{status:403})]){
 i=instance();view=()=>render(i,()=>PackageExport({caseId:'QA',title:'QA',who:WHO}));button(view(),'导出 .mcase').props.onClick();pending.shift().resolve(r);await tick();ck('bad export no download',downloads===1);unmount(i)
 }
 i=instance();view=()=>render(i,()=>PackageExport({caseId:'QA',title:'QA',who:WHO}));button(view(),'导出 .mcase').props.onClick();unmount(i);pending.shift().resolve(new Response('zip',{headers:{'Content-Type':'application/zip'}}));await tick();ck('navigation unmount suppresses download',downloads===1)
 i=instance();view=()=>render(i,()=>PackageExport({caseId:'QA',title:'QA',who:WHO}));button(view(),'导出 .mcase').props.onClick();navigate();ck('navigation intent aborts export before unmount',requests.at(-1).options.signal.aborted);pending.shift().resolve(new Response('zip',{headers:{'Content-Type':'application/zip'}}));await tick();ck('navigation intent suppresses late download',downloads===1);unmount(i)
 console.log(`${count} independent lifecycle assertions passed`)
}
checks().catch(e=>{console.error(e);process.exitCode=1})

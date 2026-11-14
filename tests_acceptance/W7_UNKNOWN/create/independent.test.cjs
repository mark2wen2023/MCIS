const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync(__dirname+'/../../../web/src/pages/RecommendationsPage.tsx','utf8'),start=src.indexOf('  const createLock =');
const block=src.slice(start,src.indexOf('  return (',start)).replace("useState<'idle' | 'sending' | 'unknown' | 'created'>",'useState').replace('api.post<Recommendation>','api.post');
class ApiError extends Error{constructor(status){super('synthetic');this.status=status}}
function env(){let cleanup,resolve,reject,identity='owner';const x={calls:[],states:[],messages:[],done:[]};
const ctx={ApiError,useRef:v=>({current:v}),useState:v=>[v,z=>(v==='idle'?x.states:x.messages).push(z)],useEffect:f=>cleanup=f(),recommendationsIdentity:()=>identity,casePath:(p,c)=>c+p,caseId:'C',f:{title:'Original',addressee:'Party',causeNodeIds:'A，B C',dueUtc:'2027-06-30',isInterim:false},onDone:id=>x.done.push(id),api:{post:(...args)=>{x.calls.push(args);return new Promise((r,j)=>{resolve=r;reject=j})}}};
vm.createContext(ctx);vm.runInContext(block+';globalThis.submit=submit',ctx);
return {ctx,x,resolve:v=>resolve(v),reject:e=>reject(e),identity:v=>identity=v,unmount:()=>cleanup()};}
(async()=>{let n=0;
for(const response of [null,{}, {caseId:'OTHER',id:'SR-2026-99'},{caseId:'C',id:99},{caseId:'C',id:'SR-2026-9'},{caseId:'C',id:'SR-2026-99\n'}]){
 const e=env(),original=JSON.stringify(e.ctx.f),p=e.ctx.submit();e.resolve(response);await p;await e.ctx.submit();
 assert.equal(e.x.states.at(-1),'unknown',JSON.stringify(response));assert.equal(e.x.done.length,0);assert.equal(e.x.calls.length,1);assert.equal(JSON.stringify(e.ctx.f),original);n++;
}
{const e=env();e.ctx.onDone=()=>{throw new ApiError(403)};const p=e.ctx.submit();e.resolve({caseId:'C',id:'SR-2026-99'});await p;await e.ctx.submit();assert.equal(e.x.states.at(-1),'created');assert.equal(e.x.calls.length,1);assert.match(e.x.messages.at(-1),/已创建.*刷新失败/);n++}
{const e=env(),p=e.ctx.submit();e.resolve({caseId:'C',id:'SR-2026-99'});await p;await e.ctx.submit();assert.equal(e.x.calls.length,1);assert.deepEqual(e.x.done,['SR-2026-99']);n++}
{const e=env(),p=e.ctx.submit();e.identity('changed');e.reject(Error('late'));await p;assert.deepEqual(e.x.states,['sending']);assert.equal(e.x.done.length,0);n++}
{const e=env();e.identity('changed');await e.ctx.submit();assert.equal(e.x.calls.length,0);n++}
console.log('PASS '+n+' independent captured source handler cases, synthetic transport');
})().catch(e=>{console.error(e);process.exitCode=1});

const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const src=fs.readFileSync(__dirname+'/../../web/src/pages/RecommendationsPage.tsx','utf8');
const block=src.slice(src.indexOf('  const responseLock ='),src.indexOf('  const saveProgress')).replace("useState<'idle' | 'sending' | 'unknown'>",'useState');
class ApiError extends Error{constructor(status){super('synthetic');this.status=status}}
function env(){let cleanup,identity='owner',resolve,reject;const x={calls:[],states:[],messages:[],text:'original',changed:0,cancelled:0};
const ctx={ApiError,useRef:v=>({current:v}),useState:v=>[v,z=>(v==='idle'?x.states:x.messages).push(z)],useEffect:f=>cleanup=f(),recommendationsIdentity:()=>identity,casePath:(p,c)=>c+p,caseId:'C',rec:{id:'R'},party:'Party',text:'original',setText:t=>x.text=t,props:{onChanged:()=>{x.changed++},onCancel:()=>{x.cancelled++}},api:{post:(...a)=>{x.calls.push(a);return new Promise((r,j)=>{resolve=r;reject=j})}}};
vm.createContext(ctx);vm.runInContext(block+';globalThis.respond=respond',ctx);
return {ctx,x,resolve:v=>resolve(v),reject:e=>reject(e),identity:v=>identity=v,unmount:()=>cleanup()};}
(async()=>{let n=0;
for(const status of [401,408,429,503]){const e=env(),p=e.ctx.respond();e.reject(new ApiError(status));await p;await e.ctx.respond();assert.equal(e.x.calls.length,1);assert.equal(e.x.states.at(-1),'unknown');assert.equal(e.x.text,'original');n++}
{const e=env();e.identity('other');await e.ctx.respond();assert.equal(e.x.calls.length,0);n++}
{const e=env();e.ctx.party='  ';await e.ctx.respond();assert.equal(e.x.calls.length,0);n++}
{const e=env();let p=e.ctx.respond();e.reject(new ApiError(422));await p;p=e.ctx.respond();e.reject(Error('network'));await p;await e.ctx.respond();assert.equal(e.x.calls.length,2);assert.equal(e.x.states.at(-1),'unknown');assert.equal(e.x.text,'original');n++}
{const e=env(),p=e.ctx.respond();e.identity('other');e.reject(Error('late'));await p;assert.deepEqual(e.x.states,['sending']);assert.equal(e.x.text,'original');n++}
for(const callback of ['onChanged','onCancel']){const e=env();e.ctx.props[callback]=()=>{throw new ApiError(403)};const p=e.ctx.respond();e.resolve({});await p;assert.equal(e.x.states.at(-1),'idle','known successful response must not become unknown due to callback failure');assert.equal(e.x.text,'');assert.match(e.x.messages.at(-1),/已登记.*刷新失败/);assert.equal(e.x.calls.length,1);n++}
console.log('PASS '+n+' independent real-handler scenarios, synthetic transport');
})().catch(e=>{console.error(e);process.exitCode=1});

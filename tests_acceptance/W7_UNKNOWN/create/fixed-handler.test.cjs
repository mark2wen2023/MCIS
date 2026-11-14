const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const s=fs.readFileSync(__dirname+'/../../../web/src/pages/RecommendationsPage.tsx','utf8');
const block=s.slice(s.indexOf('  const createLock ='),s.indexOf('  return (',s.indexOf('  const createLock =')))
 .replace("useState<'idle' | 'sending' | 'unknown' | 'created'>",'useState').replace('api.post<Recommendation>','api.post');
class ApiError extends Error{constructor(status){super();this.status=status}}
function env(){let calls=0,states=[],messages=[],clears=0,changed=0,cleanup,resolve,reject,identity='Lead\nA';let mode='pending';
 const ctx={ApiError,useRef:v=>({current:v}),useState:v=>[v,x=>(v==='idle'?states:messages).push(x)],useEffect:fn=>cleanup=fn(),recommendationsIdentity:()=>identity,casePath:p=>p,caseId:'C',f:{title:'T',addressee:'P',causeNodeIds:'N',dueUtc:'2099-01-01',isInterim:false},onDone:()=>changed++,api:{post:()=>{calls++;if(mode instanceof Error)return Promise.reject(mode);return new Promise((a,b)=>{resolve=a;reject=b})}}};
 vm.createContext(ctx);vm.runInContext(block+';globalThis.respond=submit',ctx);
 return {ctx,setMode:v=>mode=v,unmount:()=>cleanup(),setIdentity:v=>identity=v,resolve:v=>resolve(v),reject:e=>reject(e),get calls(){return calls},get states(){return states},get messages(){return messages},get clears(){return clears},get changed(){return changed}};
}
(async()=>{
 let checks=0;
 let e=env();let first=e.ctx.respond();await e.ctx.respond();assert.equal(e.calls,1);e.resolve({caseId:'C',id:'SR-2026-99'});await first;assert.equal(e.changed,1);assert.equal(e.clears,0);checks++;
 for(const err of [new TypeError('fetch failed'),new ApiError(500),new ApiError(502),new Error('parse')]){e=env();e.setMode(err);await e.ctx.respond();await e.ctx.respond();assert.equal(e.calls,1);assert.equal(e.states.at(-1),'unknown');assert.equal(e.clears,0);assert.match(e.messages.at(-1),/关闭表单、切换案件或刷新会丢失/);checks++}
 for(const status of [400,403,404,409,413,422]){e=env();e.setMode(new ApiError(status));await e.ctx.respond();await e.ctx.respond();assert.equal(e.calls,2);assert.equal(e.states.at(-1),'idle');assert.equal(e.clears,0);checks++}
 for(const fail of [false,true]){e=env();first=e.ctx.respond();e.unmount();if(fail)e.reject(new Error('late'));else e.resolve({caseId:'C',id:'SR-2026-99'});await first;assert.equal(e.changed,0);assert.equal(e.clears,0);assert.equal(e.states.length,1);checks++}
 e=env();first=e.ctx.respond();e.setIdentity('Other');e.resolve({caseId:'C',id:'SR-2026-99'});await first;assert.equal(e.changed,0);assert.equal(e.clears,0);checks++;
 assert.ok(s.includes("disabled={createState !== 'idle' || !f.title.trim() || !f.addressee.trim()}"));checks++;
 console.log(checks+' actual source handler cases passed; not browser or real identity tests');
})().catch(e=>{console.error(e);process.exitCode=1});

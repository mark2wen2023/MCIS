// Actual hook source with handwritten render/commit/cleanup. No React/browser/HTTP claim.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),ts=require('esbuild');
function harness(){
 let slots=[],cursor=0,pending=[],who='synthetic',requests=[];
 const react={useState(v){let i=cursor++;if(!(i in slots))slots[i]=typeof v==='function'?v():v;return [slots[i],v=>slots[i]=typeof v==='function'?v(slots[i]):v];},useRef(v){let i=cursor++;return slots[i]??(slots[i]={current:v});},useCallback(fn){cursor++;return fn;},useSyncExternalStore(_s,get){cursor++;return get();},useEffect(fn,deps){let i=cursor++,old=slots[i];if(!old||deps.some((v,k)=>!Object.is(v,old.deps[k])))pending.push(()=>{old?.cleanup?.();slots[i]={deps,cleanup:fn()};});}};
 const api={api:{get(url){return new Promise((resolve,reject)=>requests.push({url,resolve,reject}));}},getRole:()=>who,getOperator:()=>'',onIdentityChange:()=>()=>{}};
 return {requests,setIdentity:v=>who=v,load(file){const exports={},module={exports};vm.runInNewContext(ts.transformSync(fs.readFileSync(file,'utf8'),{loader:'ts',format:'cjs',target:'es2022'}).code,{exports,module,require:n=>n==='react'?react:api});return module.exports;},render(fn){cursor=0;return fn();},commit(){const p=pending;pending=[];p.forEach(f=>f());},unmount(){slots.forEach(s=>s?.cleanup?.());}};
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const sha=n=>n.repeat(64),pair=(c,n='a')=>[{seedSha256:sha(n),cases:[{caseId:c}]},{caseId:c,meta:{seedSha256:sha(n)}}];
async function resolve(h,i,c,n){const [l,d]=pair(c,n);h.requests[i].resolve(l);h.requests[i+1].resolve(d);await flush();}
(async()=>{
 const old=harness(),useLoad=old.load('src/hooks.ts').useLoad;let cid='SYN-A';const oldRender=()=>old.render(()=>useLoad(()=>new Promise(r=>old.requests.push({resolve:r})),[cid]));
 oldRender();old.commit();old.requests[0].resolve({caseId:cid});await flush();assert.equal(oldRender().data.caseId,cid);cid='SYN-B';assert.equal(oldRender().data.caseId,'SYN-A');old.commit();assert.equal(oldRender().data.caseId,'SYN-A');old.unmount();console.log('REPRO old useLoad retains A during B loading');
 const h=harness(),use=h.load('src/analysis/useAnalysisSnapshot.ts').useAnalysisSnapshot;cid='SYN-A';const render=()=>h.render(()=>use(cid));
 assert.equal(render().snapshot,null);h.commit();await resolve(h,0,cid);assert.equal(render().snapshot.data.caseId,cid);
 cid='SYN-B';assert.equal(render().snapshot,null);h.commit();h.requests[3].reject(Error('synthetic'));await flush();assert.equal(render().snapshot,null);assert.match(render().error,/失败/);
 render().reload();render();h.commit();await resolve(h,4,cid,'b');assert.equal(render().snapshot.data.meta.seedSha256,sha('b'));
 render().reload();render();h.commit();render().reload();await resolve(h,6,cid,'c');assert.equal(render().snapshot,null);h.commit();await resolve(h,8,cid,'d');assert.equal(render().snapshot.data.meta.seedSha256,sha('d'));
 render().reload();render();h.commit();h.requests[10].resolve(pair(cid,'a')[0]);h.requests[11].resolve(pair(cid,'b')[1]);await flush();assert.equal(render().snapshot,null);assert.match(render().error,/不一致/);
 render().reload();render();h.commit();await resolve(h,12,'SYN-WRONG');assert.equal(render().snapshot,null);
 render().reload();render();h.commit();h.setIdentity('different');await resolve(h,14,cid);assert.equal(render().snapshot,null);h.commit();await resolve(h,16,cid);assert.equal(render().snapshot.data.caseId,cid);
 cid='SYN-C';render();h.commit();cid='SYN-D';assert.equal(render().snapshot,null);h.commit();await resolve(h,20,cid);await resolve(h,18,'SYN-C');assert.equal(render().snapshot.data.caseId,'SYN-D');
 render().reload();render();h.commit();h.unmount();await resolve(h,22,cid);assert.equal(render().snapshot,null);
 const alias=harness(),aliasUse=alias.load('src/analysis/useAnalysisSnapshot.ts').useAnalysisSnapshot;const ar=()=>alias.render(()=>aliasUse('synthetic-alias'));ar();alias.commit();alias.requests[0].resolve({seedSha256:sha('a'),cases:[{caseId:'SYN-CANON',key:'synthetic-alias'}]});alias.requests[1].resolve({caseId:'SYN-CANON',key:'synthetic-alias',meta:{seedSha256:sha('a')}});await flush();assert.equal(ar().snapshot.data.caseId,'SYN-CANON');alias.unmount();
 console.log('PASS case/identity, pending/error, refresh-before-render, SHA/case mismatch, late success and unmount; controlled lifecycle only');
})().catch(e=>{console.error(e);process.exitCode=1;});

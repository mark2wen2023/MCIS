// Actual hook, synthetic effect scheduling/deferred reads. No HTTP/browser.
const assert=require('node:assert/strict'),vm=require('node:vm'),{buildSync}=require('esbuild')
const old=process.argv[2]==='baseline'
const code=buildSync({entryPoints:[old?'src/hooks.ts':'src/recommendationReview/useBoardLoad.ts'],bundle:true,platform:'node',format:'cjs',external:['*'],write:false}).outputFiles[0].text
async function scenario(mode){
 let state=[],i=0,effects=[],calls=[],identity='A'
 const react={useRef:v=>{const n=i++;if(!(n in state))state[n]={current:v};return state[n]},useState:v=>{const n=i++;if(!(n in state))state[n]=v;return[state[n],x=>state[n]=typeof x==='function'?x(state[n]):x]},useCallback:f=>{i++;return f}}
 const effect=(f,deps)=>{const n=i++,prev=state[n];if(!prev||deps.some((v,j)=>v!==prev.deps[j]))effects.push(()=>{prev?.clean?.();state[n]={deps,clean:f()}})}
 react.useEffect=effect;react.useLayoutEffect=effect
 const mods={react,'../api':{ApiError:class extends Error{},onIdentityChange:()=>()=>{},getRole:()=>identity,getOperator:()=> 'synthetic'}}
 mods['./api']=mods['../api']
 const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in mods,n);return mods[n]}})
 const loader=()=>new Promise((resolve,reject)=>calls.push({resolve,reject}))
 const render=()=>{i=0;return box.exports.useLoad(loader)}
 const flush=()=>{for(const f of effects.splice(0))f()}
 const settle=()=>new Promise(setImmediate)
 let view=render();flush()
 if(mode==='initial-error'){calls[0].reject(new Error('synthetic initial failure'));await settle();view=render();assert.equal(view.data,null);assert.equal(view.loading,false);assert.match(view.error,/initial failure/);return}
 if(mode==='retained'){calls[0].resolve('old');await settle();view=render();view.reload();render();flush();calls[1].reject(new Error('synthetic unavailable'));await settle();view=render();assert.equal(view.data,'old');assert.match(view.error,/unavailable/);assert.equal(view.loading,false);return}
 if(!['identity','unmount'].includes(mode)){view.reload();view.reload()}
 if(mode==='identity')identity='B'
 if(mode==='unmount')for(const s of state)s?.clean?.()
 if(mode==='error')calls[0].reject(new Error('old failure'));else calls[0].resolve('stale')
 await settle();view=render();assert.equal(view.data,null,'late old success must not enter current view');assert.equal(view.error,null)
 if(mode==='identity'||mode==='unmount')return
 flush();assert.equal(calls.length,2);calls[1].resolve('new');await settle();view=render();assert.equal(view.data,'new');assert.equal(view.loading,false)
}
;(async()=>{for(const m of (old?['success']:['success','error','retained','initial-error','identity','unmount']))await scenario(m);console.log('read lifecycle selected synthetic scenarios passed')})().catch(e=>{console.error(e);process.exitCode=1})

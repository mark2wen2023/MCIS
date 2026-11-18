// Synthetic hook lifecycle and API memory double only. No browser/HTTP/app or data reads.
const assert=require('node:assert/strict'),esbuild=require('esbuild'),Module=require('node:module');
(async()=>{
 let values=[],cursor=0,posts=[],resolvePost,rejectPost;globalThis.fetch=()=>{throw Error('fetch forbidden')};
 globalThis.__originTest={state(init){const i=cursor++;if(!(i in values))values[i]=typeof init==='function'?init():init;return [values[i],v=>{values[i]=typeof v==='function'?v(values[i]):v}]},ref(init){const i=cursor++;return values[i]??(values[i]={current:init})},post:(p,b)=>{posts.push(b);return new Promise((resolve,reject)=>{resolvePost=()=>resolve(b);rejectPost=reject})}};
 const out=await esbuild.build({stdin:{contents:"export {CreateObservationPanel} from './src/environment/CreateObservationPanel'; export * from './src/environment/model'",resolveDir:process.cwd(),loader:'tsx'},bundle:true,write:false,platform:'node',format:'cjs',jsx:'automatic',plugins:[{name:'memory-only',setup(b){b.onResolve({filter:/^react\/jsx-runtime$/},()=>({path:'jsx',namespace:'fake'}));b.onResolve({filter:/^react$/},()=>({path:'hooks',namespace:'fake'}));b.onResolve({filter:/^\.\.\/api$/},()=>({path:'api',namespace:'fake'}));b.onResolve({filter:/cases\/identity$/},()=>({path:'identity',namespace:'fake'}));b.onLoad({filter:/.*/,namespace:'fake'},a=>({contents:a.path==='jsx'?"export const jsx=(type,props)=>({type,props}),jsxs=jsx;":a.path==='hooks'?"export const useState=x=>globalThis.__originTest.state(x),useRef=x=>globalThis.__originTest.ref(x),useEffect=()=>{}":a.path==='identity'?"export const caseIdentity=()=> 'synthetic-session'":"export const api={post:(p,b)=>globalThis.__originTest.post(p,b),get:()=>Promise.resolve([])};export class ApiError extends Error{};export const casePath=(p,c)=>c+p",loader:'js'}))}}]});
 const m=new Module(__filename);m._compile(out.outputFiles[0].text,__filename);const lib=m.exports;
 const nodes=t=>!t||typeof t!=='object'?[]:[t,...[t.props?.children].flat(Infinity).flatMap(nodes)];
 const render=()=>{cursor=0;return lib.CreateObservationPanel({caseId:'SYNTHETIC',who:'synthetic-session',onCreated:()=>{}})};
 const click=(t,label)=>nodes(t).find(n=>n.type==='button'&&n.props.children===label).props.onClick();

 const flush=()=>new Promise(r=>setImmediate(r));
 const editOld=t=>{for(const n of nodes(t).filter(n=>['input','textarea','select'].includes(n.type)))n.props.onChange({target:{value:n.type==='select'?'Estimated':'stale'}})};
 const setup=()=>{values=[];posts=[];click(render(),'＋ 新增环境记录');const f=lib.emptyForm();Object.assign(f,{observationId:'SYNTHETIC-1',description:'synthetic description',sourceLabel:'synthetic source',valueOrigin:'Direct'});f.values.visibilityNm='0';values[1]=f;return render()};
 const submit=t=>nodes(t).find(n=>n.type==='form').props.onSubmit({preventDefault(){}});
 const failures=[];
 for(const phase of ['completed-before-render','completed-after-render','continue-new-before-render','continue-new-after-render']){
  const old=setup(),before=JSON.stringify(values[1]);submit(old);const pending=render();resolvePost();await flush();
  if(phase!=='completed-before-render'){const success=render();assert.ok(nodes(success).some(n=>n.type==='h3'));if(phase.startsWith('continue-new'))click(success,'继续新增')}
  if(phase==='continue-new-after-render')render();
  const expected=JSON.stringify(values[1]);editOld(old);editOld(pending);
  if(JSON.stringify(values[1])!==expected)failures.push(phase);
  assert.equal(posts.length,1);assert.equal(posts[0].valueOrigin,'Direct');assert.equal(posts[0].visibilityNm,0);
  if(phase.startsWith('continue-new')){const fresh=render();nodes(fresh).find(n=>n.type==='textarea').props.onChange({target:{value:'fresh'}});assert.equal(values[1].description,'fresh')}
  else assert.equal(expected,before);
 }
 // Ordinary communication error, never a permission/refusal response.
 {const old=setup();submit(old);rejectPost(Error('synthetic communication failure'));await flush();const expected=JSON.stringify(values[1]);editOld(old);if(JSON.stringify(values[1])!==expected)failures.push('unknown-before-render');let unknown=render();assert.equal(nodes(unknown).find(n=>n.type==='fieldset').props.disabled,true);editOld(unknown);assert.equal(JSON.stringify(values[1]),expected);assert.ok(values[4]);
 // Synthetic empty readback exercises existing unlock semantics; NOT proof of non-commit.
 click(unknown,'核查保存结果（只读）');await flush();const fresh=render();assert.equal(nodes(fresh).find(n=>n.type==='fieldset').props.disabled,false);nodes(fresh).find(n=>n.type==='textarea').props.onChange({target:{value:'editable after readback'}});assert.equal(values[1].description,'editable after readback');assert.equal(posts.length,1)}
 {setup();values[1].valueOrigin='';submit(render());assert.equal(posts.length,0);nodes(render()).find(n=>n.type==='select').props.onChange({target:{value:'Derived'}});assert.equal(values[1].valueOrigin,'Derived')}
 assert.deepEqual(failures,[],'retained callbacks mutated form: '+failures.join(', '));
 console.log('PASS 6 synthetic form-generation scenarios; explicit hook rerenders, not React replay/browser/HTTP');
})().catch(e=>{console.error(e);process.exitCode=1});

// Synthetic hook lifecycle and API memory double only. No browser/HTTP/app or data reads.
const assert=require('node:assert/strict'),esbuild=require('esbuild'),Module=require('node:module');
(async()=>{
 let values=[],cursor=0,posts=[],resolvePost;globalThis.fetch=()=>{throw Error('fetch forbidden')};
 globalThis.__originTest={state(init){const i=cursor++;if(!(i in values))values[i]=typeof init==='function'?init():init;return [values[i],v=>{values[i]=typeof v==='function'?v(values[i]):v}]},ref(init){const i=cursor++;return values[i]??(values[i]={current:init})},post:(p,b)=>{posts.push(b);return new Promise(resolve=>{resolvePost=()=>resolve(b)})}};
 const out=await esbuild.build({stdin:{contents:"export {CreateObservationPanel} from './src/environment/CreateObservationPanel'; export * from './src/environment/model'",resolveDir:process.cwd(),loader:'tsx'},bundle:true,write:false,platform:'node',format:'cjs',jsx:'automatic',plugins:[{name:'memory-only',setup(b){b.onResolve({filter:/^react\/jsx-runtime$/},()=>({path:'jsx',namespace:'fake'}));b.onResolve({filter:/^react$/},()=>({path:'hooks',namespace:'fake'}));b.onResolve({filter:/^\.\.\/api$/},()=>({path:'api',namespace:'fake'}));b.onResolve({filter:/cases\/identity$/},()=>({path:'identity',namespace:'fake'}));b.onLoad({filter:/.*/,namespace:'fake'},a=>({contents:a.path==='jsx'?"export const jsx=(type,props)=>({type,props}),jsxs=jsx;":a.path==='hooks'?"export const useState=x=>globalThis.__originTest.state(x),useRef=x=>globalThis.__originTest.ref(x),useEffect=()=>{}":a.path==='identity'?"export const caseIdentity=()=> 'synthetic-session'":"export const api={post:(p,b)=>globalThis.__originTest.post(p,b),get:()=>{throw Error('unexpected get')}};export class ApiError extends Error{};export const casePath=(p,c)=>c+p",loader:'js'}))}}]});
 const m=new Module(__filename);m._compile(out.outputFiles[0].text,__filename);const lib=m.exports;
 const nodes=t=>!t||typeof t!=='object'?[]:[t,...[t.props?.children].flat(Infinity).flatMap(nodes)];
 const render=()=>{cursor=0;return lib.CreateObservationPanel({caseId:'SYNTHETIC',who:'synthetic-session',onCreated:()=>{}})};
 const click=(t,label)=>nodes(t).find(n=>n.type==='button'&&n.props.children===label).props.onClick();

 for(const attempt of ['none','origin','number','all']){
  values=[];posts=[];click(render(),'＋ 新增环境记录');const f=lib.emptyForm();Object.assign(f,{observationId:'SYNTHETIC-1',description:'synthetic description',sourceLabel:'synthetic source',valueOrigin:'Direct'});f.values.visibilityNm='0';values[1]=f;const tree=render(),before=JSON.stringify(f);
  const oldSelect=nodes(tree).find(n=>n.type==='select');const oldNumbers=nodes(tree).filter(n=>n.type==='input'&&n.props.inputMode==='decimal');
  nodes(tree).find(n=>n.type==='form').props.onSubmit({preventDefault(){}});assert.equal(posts.length,1);
  // Deliberately invoke retained callbacks before a busy render: synthetic event-window probe only.
  if(attempt==='origin')oldSelect.props.onChange({target:{value:'Estimated'}});
  if(attempt==='number')oldNumbers.at(-1).props.onChange({target:{value:'7'}});
  if(attempt==='all')for(const n of nodes(tree).filter(n=>['input','textarea','select'].includes(n.type)))n.props.onChange({target:{value:n.type==='select'?'Derived':'changed'}});
  const changed=JSON.stringify(values[1])!==before;
  assert.equal(nodes(render()).find(n=>n.type==='fieldset').props.disabled,true);
  resolvePost();await new Promise(resolve=>setImmediate(resolve));const success=render();assert.ok(!nodes(success).some(n=>n.type==='form'));assert.ok(nodes(success).some(n=>n.type==='h3'&&n.props.children==='环境记录已保存'));assert.equal(posts[0].valueOrigin,'Direct');assert.equal(posts[0].visibilityNm,0);
  assert.equal(changed,false,'pending callback changed form later hidden on success: '+attempt);
  click(success,'继续新增');const next=render();assert.equal(nodes(next).find(n=>n.type==='select').props.value,'');assert.equal(values[1].description,'');assert.equal(nodes(next).find(n=>n.type==='fieldset').props.disabled,false);
  nodes(next).find(n=>n.type==='select').props.onChange({target:{value:'Estimated'}});assert.equal(values[1].valueOrigin,'Estimated');
 }
 console.log('PASS 4 synthetic pending-input scenarios: normal, origin, numeric, all inputs; confirmed snapshot, busy fieldset and continue-new');
})().catch(e=>{console.error(e);process.exitCode=1});

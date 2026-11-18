// Actual ReviewDialog, synthetic hooks/props and submit callback; no browser or HTTP.
const assert=require('node:assert/strict'),vm=require('node:vm'),{buildSync}=require('esbuild')
const code=buildSync({entryPoints:['src/reports/ReportView.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const jsx=(type,props,key)=>({type,props,key})
function nodes(n){if(!n)return[];if(Array.isArray(n))return n.flatMap(nodes);return typeof n==='object'?[n,...nodes(n.props?.children)]:[]}
function exercise(action){
 let index=0;const values=[],sent=[]
 const modules={react:{useState:v=>{const i=index++;if(!(i in values))values[i]=v;return[values[i],v=>values[i]=v]}},'react/jsx-runtime':{jsx,jsxs:jsx},'../components/Panel':{Panel:()=>null},'../config':{SERVICE_ADDR:'synthetic'},'./types':{DEMO_CASE_ID:'SYNTHETIC'}}
 const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}})
 const props={action,target:{sectionId:'SYNTHETIC',title:'synthetic',textZh:'original',textEn:'original'},busy:false,onCancel:()=>{},onSubmit:async body=>{sent.push(body);props.busy=true}}
 const render=()=>{index=0;return box.exports.ReviewDialog(props)}
 const inputs=()=>nodes(render()).filter(n=>n.type==='textarea')
 inputs().forEach((n,i)=>n.props.onChange({target:{value:'submitted '+i}}))
 const saved=inputs().map(n=>n.props.value)
 render().props.children.props.onSubmit({preventDefault:()=>{}})
 assert.equal(sent.length,1)
 inputs().forEach(n=>n.props.onChange({target:{value:'late edit'}}))
 assert.deepEqual(inputs().map(n=>n.props.value),saved,'pending edits must not become silently disposable input')
 assert.ok(inputs().every(n=>n.props.readOnly===true),'native controls read-only while saving')
 render().props.children.props.onSubmit({preventDefault:()=>{}});assert.equal(sent.length,1)
 props.busy=false;props.error='synthetic transport outcome unavailable'
 assert.deepEqual(inputs().map(n=>n.props.value),saved,'failure keeps submitted draft')
 assert.ok(inputs().every(n=>!n.props.readOnly))
 inputs()[0].props.onChange({target:{value:'after failure'}})
 assert.equal(inputs()[0].props.value,'after failure')
}
exercise('modify');exercise('dismiss')
console.log('Report review pending: 2 synthetic flows / 14 assertions passed')

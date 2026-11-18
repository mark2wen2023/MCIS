// Actual private GisisPanel exported only in the in-memory test bundle.
// Synthetic hooks and validation props; no HTTP, browser, permissions or writes.
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),{buildSync}=require('esbuild')
const code=buildSync({stdin:{contents:fs.readFileSync('src/reports/ReportView.tsx','utf8')+'\nexport { GisisPanel };',sourcefile:'ReportView.tsx',loader:'tsx'},bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['*'],write:false}).outputFiles[0].text
const jsx=(type,props,key)=>({type,props,key})
const nodes=n=>!n?[]:Array.isArray(n)?n.flatMap(nodes):typeof n==='object'?[n,...nodes(n.props?.children)]:[]
const text=n=>!n?'':Array.isArray(n)?n.map(text).join(''):typeof n==='object'?text(n.props?.children):String(n)
function exercise(select,valid){
 let i=0;const state=[],calls=[]
 const modules={react:{useState:v=>{const n=i++;if(!(n in state))state[n]=v;return[state[n],v=>state[n]=typeof v==='function'?v(state[n]):v]}},'react/jsx-runtime':{jsx,jsxs:jsx},'../components/Panel':{Panel:()=>null},'../config':{SERVICE_ADDR:'synthetic'},'./types':{DEMO_CASE_ID:'SYNTHETIC'}}
 const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>{assert.ok(n in modules,n);return modules[n]}})
 const props={data:{fields:[{id:'synthetic-field',labelZh:'合成字段',labelEn:'synthetic',value:'A',sourceRefs:[],rules:select?{enum:['A','B']}:{type:'string'}}]},busy:false,pending:false,validation:{valid,errors:valid?[]:[{fieldId:'synthetic-field',message:'old synthetic error'}],fields:[]},onExport:()=>{throw Error('not selected')},onValidate:(v,e)=>calls.push({v,e})}
 const render=()=>{i=0;return box.exports.GisisPanel(props)}
 const control=()=>nodes(render()).find(n=>n.type===(select?'select':'input'))
 assert.ok(text(render()).includes(valid?'校验通过':'old synthetic error'))
 control().props.onChange({target:{value:'B'}})
 assert.ok(!text(render()).includes('校验通过'),'edited fields must not retain old pass')
 assert.ok(!text(render()).includes('old synthetic error'),'edited fields must not retain old error details')
 assert.match(text(render()),/字段已修改.*重新校验/)
 assert.equal(control().props.value,'B')
 const button=nodes(render()).find(n=>n.type==='button'&&n.props.children==='校验字段');button.props.onClick()
 assert.equal(calls.length,1);assert.equal(calls[0].v['synthetic-field'],'B')
 props.busy=true;assert.ok(control().props.disabled)
 props.busy=false;props.validation={valid:true,errors:[],fields:[]}
 assert.ok(text(render()).includes('校验通过'),'fresh validation response can be shown')
 assert.equal(control().props.value,'B')
}
for(const select of [false,true])for(const valid of [true,false])exercise(select,valid)
console.log('GISIS validation: 4 synthetic flows / 40 assertions passed')

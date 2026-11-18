// Structural synthetic React-hook harness; not browser or assistive technology.
const assert = require('node:assert/strict')
const vm = require('node:vm')
const { buildSync } = require('esbuild')
const code = buildSync({entryPoints:['src/components/Toast.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',write:false,external:['react','react/jsx-runtime','../api']}).outputFiles[0].text
let state = null
const timers=[]
const react={createContext:()=>({Provider:'Provider'}),useState:()=>[state,v=>{state=typeof v==='function'?v(state):v}],useCallback:f=>f,useContext:()=>{}}
const jsx=(type,props)=>({type,props})
const box={exports:{}}
vm.runInNewContext(code,{module:box,exports:box.exports,require:n=>n==='react'?react:n==='react/jsx-runtime'?{jsx,jsxs:jsx}:{ApiError:class extends Error{}},window:{setTimeout:f=>timers.push(f)}})
function render(){return box.exports.ToastProvider({children:'Synthetic page'})}
function regions(tree){return tree.props.children.filter(n=>n?.props?.role)}
const initial=render()
assert.equal(regions(initial).length,2,'live regions must exist before any operation')
const show=initial.props.value
for(const [kind,role,text,other] of [['ok','status','合成保存完成','alert'],['err','alert','合成操作未完成','status']]){
  show(text,kind)
  const nodes=regions(render())
  const active=nodes.find(n=>n.props.role===role)
  assert.equal(active.props.children,text)
  assert.equal(active.props['aria-atomic'],true)
  assert.equal(active.props.className,'toast '+kind)
  const inactive=nodes.find(n=>n.props.role===other)
  assert.equal(inactive.props.children,'')
  assert.equal(inactive.props.className,undefined)
  assert.ok(nodes.every(n=>n.props.tabIndex===undefined),'feedback does not take focus')
}
timers.at(-1)()
assert.ok(regions(render()).every(n=>n.props.children===''))
console.log('toast accessibility: initial, success, error and expiry structure passed')

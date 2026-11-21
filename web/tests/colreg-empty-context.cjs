// Pure synthetic SSR. No application, effects, network, seed or business records.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const {execFileSync} = require('node:child_process')
const Module = require('node:module')
const esbuild = require('esbuild')
const React = require('react')
const {renderToStaticMarkup} = require('react-dom/server')
const root = path.resolve(__dirname, '..')
function load(source) {
  const result = esbuild.buildSync({stdin:{contents:source,resolveDir:path.join(root,'src/colreg'),loader:'tsx'},bundle:true,platform:'node',format:'cjs',write:false,packages:'external',jsx:'automatic',define:{__MCIS_API__:JSON.stringify('offline-disabled')}})
  const m = new Module(path.join(root,'tests/.synthetic.cjs'), module)
  m.filename = path.join(root,'tests/.synthetic.cjs')
  m.paths = module.paths
  m._compile(result.outputFiles[0].text,m.filename)
  return m.exports.ColregView
}
const old = load(execFileSync('git',['show','94d5e38c926fda232bb987b60fa9145e4bcf01a7:web/src/colreg/ColregView.tsx'],{encoding:'utf8'}))
const current = load(fs.readFileSync(path.join(root,'src/colreg/ColregView.tsx'),'utf8'))
const base={caseDef:{caseId:'SYN-C',caseEpochUtc:'2030-01-01T00:00:00Z',isFictionalDemo:true},vessels:[],analysis:{bands:[],checks:[]},evidence:[],audit:[],selectedId:null,onSelect(){},onReview(){}}
const render=(View,props=base)=>renderToStaticMarkup(React.createElement(View,props))
const heading=html=>html.match(/会遇局面时间带[^<]*/)[0]
assert.match(heading(render(old)),/00:00.*00:01/) // old fabricated interval, not a real band
assert.equal(heading(render(current)),'会遇局面时间带 · 尚无时间带')
assert.match(render(current),/无法据此确定分析区间/)
assert.match(render(current),/不表示无碰撞危险/)
assert.match(render(current),/供人工逐条核对/)
const populated={...base,analysis:{bands:[{bandId:'SYN-B',startTimeSec:0,endTimeSec:10,situation:'Undetermined',basis:'【推算】合成依据 <tag>'}],checks:[]}}
assert.equal(render(current,populated),render(old,populated)) // genuine zero + existing unknown/source markup unchanged
assert.match(render(current,populated),/00:00.*00:10/)
assert.match(render(current,populated),/【推算】合成依据 &lt;tag&gt;/)
console.log('PASS: old empty interval reproduced; 7 new/adjacent synthetic SSR assertions')

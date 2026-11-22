import assert from 'node:assert/strict'
import {renderToStaticMarkup} from 'react-dom/server'
import {Diagram} from '../src/bowtiePreview/Diagram'
import type {Model} from '../src/bowtiePreview/model'
const model:Model={hazard:'合成危险源',topEvent:{id:'TOP',label:'合成顶事件'},nodes:[
 {id:'T',kind:'Threat',label:'完整威胁名称超过十四个字符仍须能够读出',barrierId:null},
 {id:'P',kind:'PreventionBarrier',label:'合成预防',barrierId:null},
 {id:'M',kind:'MitigationBarrier',label:'合成减缓',barrierId:null},
 {id:'C',kind:'Consequence',label:'合成后果',barrierId:null},
 {id:'E',kind:'EscalationFactor',label:'合成升级',barrierId:'P'}],edges:[
 {fromId:'T',toId:'P'},{fromId:'P',toId:'TOP'},{fromId:'TOP',toId:'M'},{fromId:'M',toId:'C'}]}
const before=JSON.stringify(model)
const text=(m:Model)=>{const html=renderToStaticMarkup(<Diagram model={m}/>);return html.slice(html.indexOf('<details>'))}
const html=text(model)
assert.match(html,/<details><summary>查看草图文字结构/)
assert.match(html,/完整威胁名称超过十四个字符仍须能够读出/)
assert.equal((html.match(/<li>从 /g)||[]).length,4)
assert.match(html,/从 威胁「.*」（T） 指向 预防屏障「合成预防」（P）/)
assert.match(html,/从 顶事件「合成顶事件」（TOP） 指向 减缓屏障「合成减缓」（M）/)
assert.equal((html.match(/ · 屏障未知（Unknown）/g)||[]).length,2)
assert.match(html,/输入绑定屏障：预防屏障「合成预防」（P）/)
assert.match(html,/不表示已复核或因果成立/)
assert.equal(JSON.stringify(model),before)
const empty=text({hazard:'',topEvent:{id:'',label:''},nodes:[],edges:[]})
assert.match(empty,/危险源：未填写/);assert.match(empty,/没有连线/);assert.match(empty,/不代表现实中不存在/)
assert.equal((empty.match(/<li>从 /g)||[]).length,0)
const bad=text({...model,nodes:[...model.nodes,{...model.nodes[0]!}],edges:[{fromId:'T',toId:'missing'}]})
assert.match(bad,/重复 ID，端点不明确：T/);assert.match(bad,/未找到端点：missing/)
const escaped=text({...model,hazard:'<script>synthetic</script>'})
assert.ok(!escaped.includes('<script>'));assert.match(escaped,/&lt;script&gt;/)
console.log('PASS same-input Bow-tie text structure: complete labels, directed edges, Unknown, bindings, empty, ambiguous endpoints, escaping, no mutation (SSR only)')

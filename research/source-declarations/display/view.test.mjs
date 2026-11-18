import assert from 'node:assert/strict';
import {displayModel,renderDeclarationView} from './view.mjs';
import {scenario,scenarioNames} from './scenarios.mjs';
import {selectScenario,mountPrototype} from './page.mjs';
globalThis.fetch=()=>{throw Error('network forbidden')};
let groups=0;
{const m=displayModel(scenario('多角色一致'));assert.equal(m.result.status,'declarations_equal');assert.equal(m.cards.length,2);assert.ok(m.cards.every(c=>c.rows.every(r=>r.status==='声明值一致')));groups++}
{const s=scenario('ID及摘要多错'),m=displayModel(s),html=renderDeclarationView(s);assert.ok(html.includes('id_mismatch'));assert.ok(html.includes('digest_mismatch'));assert.ok(m.cards[1].rows.every(r=>r.status==='声明值不一致'));assert.ok(html.includes('整体不可确定'));groups++}
{const m=displayModel(scenario('缺失与null')),html=selectScenario('缺失与null');assert.ok(m.cards[1].rows.every(r=>r.status==='不可比较'));assert.ok(html.includes('未知（null）'));assert.ok(html.includes('缺失'));assert.ok(html.includes('字段合法（不代表一致）'));groups++}
{const html=selectScenario('同案不同笔录');assert.ok(html.includes('interview_record_mismatch'));assert.ok(html.includes('interview_snapshot_mismatch'));assert.ok(html.includes('整体不可确定'));assert.ok(html.includes('单行一致不代表整体一致'));groups++}
{for(const name of ['跨案件','显式ABA']){const m=displayModel(scenario(name));assert.ok(m.cards[1].rows.every(r=>r.status==='不可比较'));assert.notEqual(m.result.status,'declarations_equal')}groups++}
{const s=scenario('不可用');Object.defineProperty(s.pairs[1].interview,'data',{get(){throw Error('unavailable accessed')}});const html=renderDeclarationView(s);assert.ok(html.includes('上下文不可用'));assert.equal(displayModel(s).cards[1].result.fields.length,0);groups++}
{assert.ok(selectScenario('重复角色').includes('duplicate_role'));const html=selectScenario('文本转义');assert.ok(!html.includes('<script>synthetic'));assert.ok(html.includes('&lt;script&gt;'));groups++}
{for(const name of scenarioNames){const html=selectScenario(name);assert.ok(html.includes('未读取或核验原件'));assert.ok(html.includes('未证明人工批准'));assert.ok(html.includes('未建立关联'));assert.ok(!html.includes('<button'))}groups++}
// Minimal DOM stand-in exercises the actual mount/change handler, not a browser.
{const doc={createElement(tag){return {tag,children:[],value:'',innerHTML:'',setAttribute(){},append(x){this.children.push(x);if(!this.value)this.value=x.value},addEventListener(name,fn){this[name]=fn}}}};
 const root={ownerDocument:doc,replaceChildren(...children){this.children=children}};
 mountPrototype(root);const [select,out]=root.children;assert.ok(out.innerHTML.includes('整体：声明一致'));
 select.value='同案不同笔录';select.change();assert.ok(out.innerHTML.includes('INTERVIEW-B'));assert.ok(out.innerHTML.includes('interview_record_mismatch'));
 select.value='多角色一致';select.change();assert.ok(!out.innerHTML.includes('INTERVIEW-B'));assert.ok(!out.innerHTML.includes('interview_record_mismatch'));assert.ok(out.innerHTML.includes('整体：声明一致'));groups++}
{const html=selectScenario('ID及摘要多错');assert.ok(html.includes('无额外聚合问题；请查看各声明项问题。'));assert.ok(html.includes('id_mismatch'));assert.ok(html.includes('digest_mismatch'));assert.ok(!html.includes('<p>无报告问题；'));groups++}
console.log(`PASS ${groups} synthetic display groups; string rendering / DOM stand-in only`);

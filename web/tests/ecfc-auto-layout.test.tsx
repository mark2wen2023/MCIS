// Deterministic regression for the local ECFC auto-layout candidate (§4.9.2). Synthetic data only.
import {renderToStaticMarkup} from 'react-dom/server'
import {autoLayout,COLUMN,ORIGIN_X,ORIGIN_Y,ROW,type Point} from '../src/ecfcDrafts/layout'
import {Graph} from '../src/ecfcDrafts/Graph'
import {equal,type Draft,type Node,type Validation} from '../src/ecfcDrafts/model'
let passed=0
const ok=(c:unknown,m:string)=>{if(!c)throw Error('FAIL: '+m);passed++}
const freeze=<T,>(v:T):T=>{if(v&&typeof v==='object'){Object.freeze(v);for(const k of Object.keys(v))freeze((v as Record<string,unknown>)[k])}return v}
const ev=(id:string,lane=0,timeSeconds:number|null=null,evidenceIds:string[]=[]):Node=>({id,kind:'Event',text:`合成事件 ${id}`,timeSeconds,lane,isPrimaryIncident:false,evidenceIds})
const co=(id:string,lane:number):Node=>({id,kind:'Condition',text:`合成条件 ${id}`,timeSeconds:null,lane,isPrimaryIncident:false,evidenceIds:[]})
const col=(p:Point)=>(p.x-ORIGIN_X)/COLUMN
const laid=(d:Draft,m?:Map<string,Point>)=>{const r=autoLayout(d,m);if(r.status!=='laid-out')throw Error('expected laid-out');return r}
const validation=(d:Draft):Validation=>({coreVersion:'mcis-ecfc-draft/1',nodes:d.nodes.map(n=>({...n,isPresumptive:true as const})),edges:d.edges.map(e=>{const a=d.nodes.find(n=>n.id===e.from)!,b=d.nodes.find(n=>n.id===e.to)!;return {...e,kind:a.kind==='Event'?'Sequence' as const:'Influence' as const,bold:a.kind==='Event'&&a.lane===0&&b.lane===0}}),issues:[]})

// 1. Untimed Z->A: topological, not alphabetical or input order; secondary event pointing at A aligns with A.
const zToA:Draft={scope:'合成未定时 Z→A 布局回归',nodes:[{...ev('A',0,null,['EV-001']),isPrimaryIncident:true},ev('M'),ev('Z'),ev('S',1),co('C1',-1)],edges:[{id:'e1',from:'Z',to:'M'},{id:'e2',from:'M',to:'A'},{id:'e3',from:'S',to:'A'},{id:'e4',from:'C1',to:'M'}]}
const doc=freeze({caseId:'SYNTHETIC-LAYOUT',revision:3,draft:zToA,sources:[{evidenceId:'EV-001',title:'合成证据',sha256:'0'.repeat(64)}]})
const before=JSON.stringify(doc),snapshot=structuredClone(doc)
const r1=laid(doc.draft),p=r1.positions
ok(col(p.get('Z')!)===0&&col(p.get('M')!)===1&&col(p.get('A')!)===2,'main sequence Z,M,A topological (alphabetical/input would be A,M,Z)')
ok(p.get('Z')!.y===p.get('M')!.y&&p.get('M')!.y===p.get('A')!.y,'main sequence on one row')
ok(p.get('S')!.x===p.get('A')!.x,'secondary event S x aligned with A')
ok(p.get('S')!.y===ORIGIN_Y+2*ROW&&p.get('A')!.y===ORIGIN_Y+ROW,'lane rows: -1,0,1 ordered')
ok(p.get('C1')!.x===p.get('M')!.x&&p.get('C1')!.y<p.get('M')!.y,'condition sits above the event it influences')
ok(r1.pending.length===0&&r1.manualKept.length===0,'no pending for fully determined chain')
ok(JSON.stringify(doc)===before&&equal(doc,snapshot),'case id, nodes, edge endpoints, times, text, evidence unchanged')
ok(zToA.nodes.every(n=>n.timeSeconds===null),'no time guessed')
ok(equal(laid(doc.draft).positions,r1.positions)&&JSON.stringify([...laid(doc.draft).positions])===JSON.stringify([...p]),'deterministic repeat')
// 2. Timed main sequence keeps existing time-then-id rule.
const timed:Draft={scope:'合成定时',nodes:[ev('T3',0,30),ev('T2',0,10),ev('T1',0,10)],edges:[]}
const r2=laid(freeze(timed))
ok(col(r2.positions.get('T1')!)===0&&col(r2.positions.get('T2')!)===1&&col(r2.positions.get('T3')!)===2,'timed: time then id')
ok(timed.nodes.map(n=>n.timeSeconds).join()==='30,10,10','times retained')
// 3. Undeterminable order stays pending.
const amb=laid(freeze({scope:'合成不确定',nodes:[ev('P'),ev('Q')],edges:[]}))
ok(amb.pending.map(x=>x.nodeId).join()==='P,Q'&&amb.pending.every(x=>x.reason.includes('待核')),'untimed unrelated nodes pending, not guessed')
// 4. Mixed: timed ready node and untimed ready node -> untimed flagged.
const mix=laid(freeze({scope:'合成混合',nodes:[ev('U'),ev('K',0,5)],edges:[]}))
ok(mix.pending.some(x=>x.nodeId==='U'),'mixed untimed tie pending')
// 5. Secondary event without main target pending.
const orphan=laid(freeze({scope:'合成孤立',nodes:[ev('A'),ev('X',2)],edges:[]}))
ok(orphan.pending.some(x=>x.nodeId==='X'),'secondary without main target pending')
// 6. Manual positions never overwritten; others identical.
const manual=new Map([['M',{x:5,y:7}]]),r6=laid(doc.draft,manual)
ok(r6.positions.get('M')!.x===5&&r6.positions.get('M')!.y===7&&r6.manualKept.join()==='M','manual position kept')
ok(['Z','A','S','C1'].every(id=>equal(r6.positions.get(id),p.get(id))),'other nodes unchanged by manual')
ok(manual.get('M')!.x===5&&manual.size===1,'manual map not mutated')
// 7. Cycle and invalid input are not shown as completed.
const cyc=autoLayout(freeze({scope:'合成循环',nodes:[ev('A'),ev('Z')],edges:[{id:'c1',from:'Z',to:'A'},{id:'c2',from:'A',to:'Z'}]}))
ok(cyc.status==='invalid'&&!('positions' in cyc),'cycle -> invalid, no layout')
const bad=autoLayout(freeze({scope:'合成非法',nodes:[ev('A')],edges:[{id:'b1',from:'A',to:'NOPE'}]}))
ok(bad.status==='invalid','dangling edge -> invalid')
const bad2=autoLayout({scope:'合成非法2',nodes:[ev('A'),ev('A')],edges:[]})
ok(bad2.status==='invalid','duplicate id -> invalid')
// 8. Existing candidate UI: default stays input-order schematic, explicit control present.
const html=renderToStaticMarkup(<Graph draft={doc.draft} validation={validation(doc.draft)}/>)
ok(html.includes('自动布局（仅调整显示坐标）')&&html.includes('aria-pressed="false"'),'explicit layout control rendered, off by default')
ok(html.includes('示意布局：节点按输入顺序排列')&&html.includes('data-node-id="A" data-x="160"'),'default schematic unchanged (A first by input order)')
console.log(`ECFC auto-layout deterministic checks passed: ${passed}`)

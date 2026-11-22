import assert from 'node:assert/strict'
import {renderToStaticMarkup} from 'react-dom/server'
import {Graph} from '../../web/src/ecfcDrafts/Graph'
import {EdgeSelection,edgeSelection,savedEdgeView} from '../../web/src/ecfcDrafts/EdgeSelection'
import {CORE,PROFILE,type Draft,type Document,type Validation} from '../../web/src/ecfcDrafts/model'
import {begin,reset} from './hooks'
import {setResponse} from './api'
// run.cjs appends this test-only export to the real Panel module in memory.
import {Editor} from '../../web/src/ecfcDrafts/Panel'
import {caseIdentity} from '../../web/src/cases/identity'
let count=0
const pass=(name:string)=>{count++;console.log('PASS '+name)}
const draft:Draft={scope:'Synthetic',nodes:[{id:'A',kind:'Event',text:'Synthetic A',timeSeconds:null,lane:0,isPrimaryIncident:false,evidenceIds:[]},{id:'B',kind:'Event',text:'Synthetic B',timeSeconds:0,lane:0,isPrimaryIncident:false,evidenceIds:[]}],edges:[{id:'E',from:'A',to:'B'}]}
const validation:Validation={coreVersion:CORE,nodes:draft.nodes.map(n=>({...n,isPresumptive:true})),edges:[{...draft.edges[0]!,kind:'Sequence',bold:true}],issues:[]}
const doc:Document={caseId:'SYN',revision:1,digest:'a'.repeat(64),draft,sources:[],validation,status:'Draft',strength:'ToBeVerified',origin:'Investigator',savedBy:'Synthetic',savedRole:'Investigator',savedUtc:'2026-01-01T00:00:00Z'}
const frame=(context:any)=>({context,locator:'/fragments/0',sourceUtc:'2026-02-01T12:00:37.000Z',excerpt:'Synthetic <fragment>'})
function all(tree:any,p:(e:any)=>boolean):any[]{if(!tree||typeof tree!=='object')return [];if(Array.isArray(tree))return tree.flatMap(e=>all(e,p));return [...(p(tree)?[tree]:[]),...all(tree.props?.children,p)]}
function deferred(){let resolve!:(v:any)=>void,reject!:(e:any)=>void;const promise=new Promise<any>((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject}}
async function main(){
 const defaultHtml=renderToStaticMarkup(<EdgeSelection draft={draft} validation={validation} document={doc}/>)
 assert.match(defaultHtml,/可信边关联尚未接通/);assert.ok(!defaultHtml.includes('查看该连线关联出处</button>'))
 pass('real integrated view defaults to unavailable, no read action')
 const selected:any[]=[];const graph=Graph({draft,validation,onSelectEdge:e=>selected.push(e.id),selectedEdge:'E'})
 const svg=all(graph,e=>e.type==='g'&&e.props.onClick)[0],button=all(graph,e=>e.type==='button')[0]
 svg.props.onClick();button.props.onClick();assert.deepEqual(selected,['E','E']);assert.equal(button.props['aria-pressed'],true)
 pass('real Graph SVG and native button share selection callback and highlight')
 const good={dirty:false,busy:false,sourceAck:true,sourcesCurrent:true,needReopen:false,blocked:false}
 assert.ok(savedEdgeView(doc,draft,good));for(const key of ['dirty','busy','needReopen','blocked'])assert.ok(!savedEdgeView(doc,draft,{...good,[key]:true}))
 for(const key of ['sourceAck','sourcesCurrent'])assert.ok(!savedEdgeView(doc,draft,{...good,[key]:false}))
 const changed=structuredClone(draft);changed.nodes[0]!.text='Changed, same edge';assert.ok(!savedEdgeView(doc,changed,good))
 pass('saved exact draft and source eligibility; no writeAllowed gate')
 for(const lateFailure of [false,true]){
  const late=deferred();let reads=0;const session=edgeSelection(doc,async()=>{reads++;return late.promise})
  session.select(draft.edges[0]!);const loading=session.read();assert.equal(session.snapshot().status,'pending');session.close()
  if(lateFailure)late.reject(Error('DO NOT DISPLAY'));else late.resolve(frame({caseId:'SYN',revision:1,digest:doc.digest,edgeId:'E',from:'A',to:'B'}))
  await loading;assert.equal(reads,1);assert.equal(session.snapshot().frame,null);assert.equal(session.snapshot().status,'empty')
 }
 pass('unmounted/invalidated selection ignores late success and failure')
 const session=edgeSelection(doc,async c=>frame(c));session.select(draft.edges[0]!);await session.read();assert.equal(session.snapshot().frame?.locator,'/fragments/0');session.select(draft.edges[0]!);assert.equal(session.snapshot().frame,null)
 const v2={...doc,revision:2,digest:'b'.repeat(64)};const wrong=edgeSelection(v2,async c=>frame({...c,revision:1}));wrong.select(draft.edges[0]!);await wrong.read();assert.equal(wrong.snapshot().status,'unavailable');assert.equal(wrong.snapshot().frame,null)
 const next=edgeSelection(v2,async c=>frame(c));next.select(draft.edges[0]!);await next.read();assert.equal(next.snapshot().frame?.context.revision,2)
 pass('new revision requires own mapping; wrong revision has no content')
 const context={profile:PROFILE,caseId:'SYN',sources:[],writeAllowed:false,identityMode:'local-role-header',sourceBinding:'registered-metadata-only',archiveSupported:false}
 const props:any={caseId:'SYN',who:caseIdentity(),context,envelope:{profile:PROFILE,caseId:'SYN',document:doc,sourceStatus:'unchanged',persisted:true,identityMode:'local-role-header'},reopen(){},recovery:false,candidateEdgeReader:async(c:any)=>frame(c)}
 const render=()=>{begin();return Editor(props)}
 reset();let tree=render();let view=all(tree,e=>e.type===EdgeSelection)[0];assert.equal(view.props.document,doc);assert.equal(view.props.reader,props.candidateEdgeReader)
 pass('actual Editor read-only state retains candidate read eligibility')
 props.context={...context,writeAllowed:true};reset();tree=render();const oldKey=all(tree,e=>e.type===EdgeSelection)[0].key
 const textarea=all(tree,e=>e.type==='textarea'&&e.props.value==='Synthetic A')[0];textarea.props.onChange({target:{value:'Edited A'}})
 tree=render();assert.equal(all(tree,e=>e.type===EdgeSelection).length,0)
 const modified=structuredClone(draft);modified.nodes[0]!.text='Edited A';const pv={...validation,nodes:modified.nodes.map(n=>({...n,isPresumptive:true}))}
 setResponse({profile:PROFILE,caseId:'SYN',draft:modified,validation:pv,persisted:false})
 const preview=all(tree,e=>e.type==='button'&&String(e.props.children).startsWith('预览结构'))[0];preview.props.onClick();await Promise.resolve();await Promise.resolve()
 tree=render();view=all(tree,e=>e.type===EdgeSelection)[0];assert.ok(view);assert.equal(view.props.document,null);assert.equal(view.props.reader,undefined);assert.notEqual(view.key,oldKey)
 pass('actual Editor node-text edit clears view; repreview same edge never revives saved source')
 // Real save callback with an explicitly synthetic confirmed response. No HTTP/DB writes.
 const backup=all(tree,e=>e.type==='input'&&e.props.type==='checkbox'&&e.props.checked===false&&e.props.disabled===false).at(-1)
 assert.ok(backup);backup.props.onChange({target:{checked:true}});tree=render()
 setResponse((_case:any,_who:any,_action:any,_signal:any,body:any)=>({profile:PROFILE,caseId:'SYN',document:{...doc,revision:2,digest:'b'.repeat(64),draft:body.draft,sources:body.expectedSources,validation:pv,savedBy:'调查员 A'},sourceStatus:'unchanged',persisted:true,identityMode:'local-role-header'}))
 const save=all(tree,e=>e.type==='button'&&e.props.children==='保存 ECFC 人工草稿')[0];save.props.onClick();await Promise.resolve();await Promise.resolve()
 tree=render();view=all(tree,e=>e.type===EdgeSelection)[0];assert.equal(view.props.document,null)
 assert.ok(all(tree,e=>e.type==='p'&&String(e.props.children).includes('请先重新打开服务端草稿')).length)
 pass('actual save receipt still requires reopen before source read')

 for(const patch of [{sourceStatus:'changed'},{caseId:'OTHER'}]){reset();props.envelope={...props.envelope,...patch};tree=render();view=all(tree,e=>e.type===EdgeSelection)[0];assert.equal(view.props.document,null);props.envelope={...props.envelope,caseId:'SYN',sourceStatus:'unchanged'}}
 pass('actual Editor changed sources or mismatched case has no eligible reader')
 const html=renderToStaticMarkup(<EdgeSelection draft={draft} validation={validation} document={doc} reader={props.candidateEdgeReader}/>)
 assert.match(html,/不提供回放跳转/);assert.ok(!html.includes('href='));assert.match(html,/待核验/)
 pass('source UTC never grants seek; no link or persistence controls')
 console.log(`${count} scenarios passed; real Graph SSR + actual Editor callbacks with handwritten hooks; no browser/effects/HTTP`)
}
main().catch(e=>{console.error(e);process.exitCode=1})

import {useEffect,useMemo,useSyncExternalStore} from 'react'
import {Graph} from './Graph'
import {equal,type Draft,type Validation,type Document,type Edge} from './model'

// Composition-only candidate seam. No default reader, endpoint, identity or authority.
// Only synthetic tests supply this callback. A future server association must be reviewed.
export type EdgeContext={caseId:string;revision:number;digest:string;edgeId:string;from:string;to:string}
export type EdgeFrame={context:EdgeContext;locator:string;sourceUtc:string|null;excerpt:string}
export type CandidateEdgeReader=(context:EdgeContext)=>Promise<EdgeFrame>
type State={edge:Edge|null;status:'empty'|'pending'|'ready'|'unavailable';frame:EdgeFrame|null}
export function savedEdgeView(document:Document|null,draft:Draft,flags:{dirty:boolean;busy:boolean;sourceAck:boolean;sourcesCurrent:boolean;needReopen:boolean;blocked:boolean}){
 return !!document&&!flags.dirty&&!flags.busy&&flags.sourceAck&&flags.sourcesCurrent&&!flags.needReopen&&!flags.blocked&&equal(document.draft,draft)
}
export function edgeSelection(document:Document|null,reader?:CandidateEdgeReader){
 let state:State={edge:null,status:'empty',frame:null},serial=0,live=true
 const listeners=new Set<()=>void>(),emit=(s:State)=>{state=s;listeners.forEach(fn=>fn())}
 return {
  snapshot:()=>state,subscribe(fn:()=>void){listeners.add(fn);return()=>{listeners.delete(fn)}},
  activate(){live=true},close(){live=false;serial++;state={edge:null,status:'empty',frame:null}},
  select(edge:Edge){if(!live)return;serial++;emit({edge:{id:edge.id,from:edge.from,to:edge.to},status:'empty',frame:null})},
  async read(){
   const edge=state.edge;if(!live||!edge||!document||!reader||state.status==='pending')return
   if(!document.draft.edges.some(e=>equal(e,edge)))return
   const ticket=++serial,context={caseId:document.caseId,revision:document.revision,digest:document.digest,edgeId:edge.id,from:edge.from,to:edge.to}
   emit({edge,status:'pending',frame:null})
   try{
    const frame=await reader({...context})
    if(!live||ticket!==serial)return
    if(!frame||!equal(frame.context,context)||typeof frame.locator!=='string'||!/^\/(?:[^~\s]|~[01]){1,240}$/.test(frame.locator)||typeof frame.excerpt!=='string'||frame.excerpt.length>1000||!(frame.sourceUtc===null||typeof frame.sourceUtc==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(frame.sourceUtc)&&Number.isFinite(Date.parse(frame.sourceUtc))&&new Date(frame.sourceUtc).toISOString()===frame.sourceUtc))throw Error()
    emit({edge,status:'ready',frame:{context,locator:frame.locator,sourceUtc:frame.sourceUtc,excerpt:frame.excerpt}})
   }catch{if(live&&ticket===serial)emit({edge,status:'unavailable',frame:null})}
  }
 }
}
// Panel keys this subtree by verified saved context and eligibility. Editing unmounts it.
export function EdgeSelection({draft,validation,document,reader}:{draft:Draft;validation:Validation;document:Document|null;reader?:CandidateEdgeReader}){
 const session=useMemo(()=>edgeSelection(document,reader),[document,reader])
 useEffect(()=>{session.activate();return()=>session.close()},[session])
 const state=useSyncExternalStore(session.subscribe,session.snapshot,session.snapshot)
 return <><Graph draft={draft} validation={validation} selectedEdge={state.edge?.id} onSelectEdge={session.select}/>
 <aside aria-label="连线出处核对"><h3>连线出处 · 待核验</h3><p>关联不证明因果；原始记录时刻不是已核实事件时刻，不提供回放跳转。</p>
 {!document?<p>须重新打开已保存、来源已核对且未修改的草稿；重新预览不能恢复旧出处。</p>:!reader?<p>可信边关联尚未接通；未读取原件。</p>:<p>仅候选读取器；仍须服务端独立核验关联与读取权限。</p>}
 {state.edge&&<p>所选连线 {state.edge.id}：{state.edge.from} → {state.edge.to}</p>}
 {document&&reader&&<button type="button" disabled={!state.edge||state.status==='pending'} onClick={()=>void session.read()}>查看该连线关联出处</button>}
 {state.status==='pending'&&<p role="status">正在核对该版本关联…</p>}{state.status==='unavailable'&&<p role="alert">出处不可用；未显示旧内容。</p>}
 {state.frame&&<dl><dt>原始记录定位</dt><dd>{state.frame.locator}</dd><dt>原始记录 UTC（非事件时刻）</dt><dd>{state.frame.sourceUtc??'未知'}</dd><dt>关联片段（待核验）</dt><dd>{state.frame.excerpt}</dd></dl>}
 </aside></>
}

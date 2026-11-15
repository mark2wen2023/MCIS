import type {Observation} from '../types'
import type {EditableConflict,VersionedConflict} from './conflictEditing'
import {editableRows} from './conflictEditing'
export type Receipt={receiptId:string;caseId:string;conflictId:string;conflictVersion:string;expiresUtc:string;kind:string;bytesVerified:false;humanReadVerified:false;identityVerified:false;sources:Record<string,{sha256:string;registryDocSha256:string;custodyHeadSeq:number|null;custodyHeadSha256:string|null;bytesVerified:false}>}
type Transport={get:(path:string)=>Promise<unknown>;post:(path:string,body:unknown)=>Promise<unknown>}
// Compare JSON values independent of object key order; do not coerce response types.
function canonical(v:unknown):string {
  if(Array.isArray(v))return '['+v.map(canonical).join(',')+']'
  if(v!==null&&typeof v==='object')return '{'+Object.entries(v).sort(([a],[b])=>a<b?-1:a>b?1:0).map(([k,x])=>JSON.stringify(k)+':'+canonical(x)).join(',')+'}'
  return JSON.stringify(v)
}
const hash=(v:unknown)=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v)
export class ObservationEditing {
  private listeners=new Set<()=>void>()
  private generation=0
  private confirmedText:{a:string;b:string}
  state:{current:EditableConflict;draft:{a:Observation;b:Observation};allowed:boolean;busy:boolean;receipt:Receipt|null;error:string;message:string}
  private caseId:string
  private http:Transport
  private saved:()=>void
  private now:()=>number
  constructor(caseId:string,row:EditableConflict,http:Transport,saved:()=>void,now=()=>Date.now()){
    this.confirmedText={a:row.a.valueText,b:row.b.valueText}
    this.caseId=caseId;this.http=http;this.saved=saved;this.now=now
    this.state={current:structuredClone(row),draft:structuredClone({a:row.a,b:row.b}),allowed:false,busy:false,receipt:null,error:'',message:''}
  }
  hasUnsavedInput=()=>this.state.draft.a.valueText!==this.confirmedText.a||this.state.draft.b.valueText!==this.confirmedText.b
  subscribe=(fn:()=>void)=>{this.listeners.add(fn);return ()=>{this.listeners.delete(fn)}}
  snapshot=()=>this.state
  private update(p:Partial<typeof this.state>){this.state={...this.state,...p};this.listeners.forEach(f=>f())}
  private path(suffix=''){return `/cases/${encodeURIComponent(this.caseId)}/conflicts${suffix}`}
  identityChanged=()=>{this.generation++;this.update({allowed:false,receipt:null,busy:false,message:'身份声明已变化，请重新检查来源权限；草稿仍在本页内存。'})}
  edit(side:'a'|'b',text:string){if(this.state.busy)return;this.update({draft:{...this.state.draft,[side]:{...this.state.draft[side],valueText:text}},receipt:null,message:''})}
  private async action(fn:(generation:number)=>Promise<void>){
    if(this.state.busy)return
    const g=this.generation;this.update({busy:true,error:'',message:''})
    try{await fn(g)}catch(e){if(g===this.generation){const status=(e as {status?:number}).status;this.update({receipt:null,...(status===403?{allowed:false}:{}),error:status===403?'来源访问未获准；观察草稿保留，仍可使用原有说明／状态编辑。':(status===409||status===412||status===428)?'服务端拒绝本次操作；草稿保留。请重新核对当前记录及登记版本，不会自动重试。':'操作结果未确认或回执不可用；草稿保留。请先读取当前记录核对是否已保存，不要直接重试。'})}}
    finally{if(g===this.generation)this.update({busy:false})}
  }
  check=()=>this.action(async g=>{
    const r=await this.http.get(this.path(`/${encodeURIComponent(this.state.current.conflictId)}/revisions`)) as {caseId?:string;conflictId?:string;revisions?:unknown}
    if(r?.caseId!==this.caseId||r.conflictId!==this.state.current.conflictId||!Array.isArray(r.revisions))throw Error('history shape')
    if(g===this.generation)this.update({allowed:true,message:'来源历史访问检查通过；保存时服务端仍会重新检查权限。'})
  })
  // Explicit refresh/adoption action: never overwrites the user's proposed observations.
  refresh=()=>this.action(async g=>{
    const raw=await this.http.get(this.path(':editable')) as VersionedConflict[]
    const next=editableRows(raw).find(x=>x.conflictId===this.state.current.conflictId)
    if(!next)throw Error('missing')
    if((['a','b'] as const).some(side=>next[side].evidenceId!==this.state.draft[side].evidenceId))throw Error('source identity changed')
    const draft={a:{...next.a,valueText:this.state.draft.a.valueText},b:{...next.b,valueText:this.state.draft.b.valueText}}
    if(g===this.generation){this.confirmedText={a:next.a.valueText,b:next.b.valueText};this.update({current:next,draft,receipt:null,message:'已读取当前记录并采用其编辑版本；草稿未覆盖。请逐侧比对后重新取得登记回执。'})}
  })
  issue=()=>this.action(async g=>{
    if(!this.state.allowed)throw Error('permission')
    const observations=structuredClone(this.state.draft)
    const refs=new Set<string>()
    for(const side of ['a','b'] as const)if(canonical(this.state.current[side])!==canonical(observations[side])){
      for(const obs of [this.state.current[side],observations[side]]){
        if(typeof obs.evidenceId!=='string'||!obs.evidenceId)throw Error('unknown source')
        refs.add(obs.evidenceId)
      }
    }
    if(!refs.size)throw Error('unchanged observations')
    const raw=await this.http.post(this.path(`/${encodeURIComponent(this.state.current.conflictId)}/source-receipts`),{expectedVersion:this.state.current.expectedVersion,observations}) as Receipt
    if(!raw||raw.kind!=='registry-observation-v1'||raw.caseId!==this.caseId||raw.conflictId!==this.state.current.conflictId||raw.conflictVersion!==this.state.current.expectedVersion||typeof raw.receiptId!=='string'||!/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(raw.receiptId)||raw.bytesVerified!==false||raw.humanReadVerified!==false||raw.identityVerified!==false||typeof raw.expiresUtc!=='string'||!Number.isFinite(Date.parse(raw.expiresUtc))||Date.parse(raw.expiresUtc)<=this.now()||!raw.sources||typeof raw.sources!=='object'||Array.isArray(raw.sources)||!Object.keys(raw.sources).length)throw Error('receipt')
    if(!hash(raw.conflictVersion)||Object.keys(raw.sources).length!==refs.size||Object.keys(raw.sources).some(id=>!refs.has(id)))throw Error('source set')
    for(const source of Object.values(raw.sources)){
      if(!source||typeof source!=='object'||Array.isArray(source)||!hash(source.sha256)||!hash(source.registryDocSha256)||source.bytesVerified!==false)throw Error('source')
      if(source.custodyHeadSeq===null){if(source.custodyHeadSha256!==null)throw Error('custody')}
      else if(!Number.isSafeInteger(source.custodyHeadSeq)||source.custodyHeadSeq<1||!hash(source.custodyHeadSha256))throw Error('custody')
    }
    if(g===this.generation)this.update({receipt:structuredClone(raw),message:'登记回执已取得；请核对下列版本后显式提交。这不证明您已读原件。'})
  })
  submit=()=>this.action(async g=>{
    const r=this.state.receipt
    if(!this.state.allowed||!r||Date.parse(r.expiresUtc)<=this.now())throw Error('expired')
    const {expectedVersion,...current}=this.state.current
    const expected={...current,...structuredClone(this.state.draft),caseId:this.caseId}
    const response=await this.http.post(this.path(),{...expected,expectedVersion,sourceReceiptId:r.receiptId})
    // Server returns the persisted conflict document, without request-only fields.
    if(canonical(response)!==canonical(expected))throw Error('unconfirmed save response')
    if(g===this.generation){this.confirmedText={a:expected.a.valueText,b:expected.b.valueText};this.update({receipt:null,allowed:false,message:'观察修改已保存；不代表原件核验或事实批准。草稿仍保留，继续编辑前须显式读取当前记录。'});this.saved()}
  })
}

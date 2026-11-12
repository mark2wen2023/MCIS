import {useEffect,useRef,useState} from 'react'
import {onIdentityChange} from '../api'
import {caseIdentity} from '../cases/identity'
import {onPackageNavigation} from '../packages/navigation'
import {parsePreview,validateInput,inputHash,SourceChangedError,type Input,type Interval,type Preview,type Source} from './model'
import {restRequest,restError} from './api'
import {RestResult} from './Result'
const blank=():Interval=>({startUtc:'',endUtc:'',kind:'Watch'})
export function RestForm({caseId,who,sources}:{caseId:string;who:string;sources:Source[]}){
 const [input,setInput]=useState<Input>({recordStartUtc:'',recordEndUtc:'',intervals:[blank()],sourceEvidenceIds:[]}),[preview,setPreview]=useState<Preview|null>(null),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[confirmed,setConfirmed]=useState(false),[sourceStale,setSourceStale]=useState(false)
 const gen=useRef(0),active=useRef(true),controller=useRef<AbortController|null>(null),lock=useRef(false)
 const clear=()=>{gen.current++;controller.current?.abort();controller.current=null;lock.current=false;setPreview(null);setMessage('');setBusy(false)}
 useEffect(()=>{active.current=true;const cancel=()=>{clear();setConfirmed(false)};const a=onIdentityChange(cancel),b=onPackageNavigation(cancel);return()=>{active.current=false;gen.current++;controller.current?.abort();a();b()}},[])
 const edit=(next:Input)=>{clear();setConfirmed(false);setInput(next)}
 async function calculate(){
  if(lock.current||caseIdentity()!==who||!confirmed||sourceStale)return
  clear();try{validateInput(input)}catch(e){setMessage(e instanceof Error?e.message:'输入无效');return}
  const selected=sources.filter(s=>input.sourceEvidenceIds.includes(s.evidenceId)).map(s=>({...s}))
  const version=++gen.current,c=new AbortController();controller.current=c;lock.current=true;setBusy(true)
  const valid=()=>active.current&&version===gen.current&&caseIdentity()===who
  try{const expectedHash=await inputHash(caseId,input,selected);if(!valid())return;const raw=await restRequest(caseId,who,'preview',c.signal,input);if(!valid())return;const p=parsePreview(raw,caseId,input,expectedHash,selected);if(valid())setPreview(p)}catch(e){if(valid()){if(e instanceof SourceChangedError){setInput(old=>({...old,sourceEvidenceIds:[]}));setConfirmed(false);setSourceStale(true)}setMessage(e instanceof SourceChangedError?e.message:restError(e))}}finally{if(valid()){setBusy(false);lock.current=false}}
 }
 return <div className="w183-form"><h2>人工录入记录</h2><p>所有时间用 UTC 整秒，格式 YYYY-MM-DDTHH:mm:ssZ。工程年份范围1900–2100，最长14天、1至256个不重叠时段。未标注的时间是 Unknown，不默认计作休息。</p><div className="w183-range"><label>记录起点 UTC<input value={input.recordStartUtc} placeholder="YYYY-MM-DDTHH:mm:ssZ" onChange={e=>edit({...input,recordStartUtc:e.target.value})}/></label><label>记录终点 UTC<input value={input.recordEndUtc} placeholder="YYYY-MM-DDTHH:mm:ssZ" onChange={e=>edit({...input,recordEndUtc:e.target.value})}/></label></div>
 <fieldset><legend>工休时段</legend>{input.intervals.map((row,i)=><div className="w183-row" key={i}><span>#{i+1}</span><label>开始 UTC {i+1}<input value={row.startUtc} onChange={e=>edit({...input,intervals:input.intervals.map((x,j)=>i===j?{...x,startUtc:e.target.value}:x)})}/></label><label>结束 UTC {i+1}<input value={row.endUtc} onChange={e=>edit({...input,intervals:input.intervals.map((x,j)=>i===j?{...x,endUtc:e.target.value}:x)})}/></label><label>类型 {i+1}<select aria-label={'类型 '+(i+1)} value={row.kind} onChange={e=>edit({...input,intervals:input.intervals.map((x,j)=>i===j?{...x,kind:e.target.value as Interval['kind']}:x)})}><option value="Watch">值班 Watch</option><option value="OtherWork">其他工作 OtherWork</option><option value="Rest">休息 Rest</option></select></label><button type="button" aria-label={'删除时段 '+(i+1)} disabled={input.intervals.length<=1} onClick={()=>edit({...input,intervals:input.intervals.filter((_,j)=>j!==i)})}>删除</button></div>)}<button type="button" disabled={input.intervals.length>=256} onClick={()=>edit({...input,intervals:[...input.intervals,blank()]})}>添加时段</button></fieldset>
 <fieldset><legend>本案登记来源（选择1至8条）</legend><p>来源只绑定证据登记的标题和 SHA-256。人工录入尚未验证，系统不读取原件确认内容一致。</p>{sourceStale?<p>来源登记已变化，旧来源列表已隐藏。请使用上方刷新来源重新读取。</p>:sources.length?sources.map(s=><label className="w183-source" key={s.evidenceId}><input type="checkbox" checked={input.sourceEvidenceIds.includes(s.evidenceId)} disabled={!input.sourceEvidenceIds.includes(s.evidenceId)&&input.sourceEvidenceIds.length>=8} onChange={e=>edit({...input,sourceEvidenceIds:e.target.checked?[...input.sourceEvidenceIds,s.evidenceId]:input.sourceEvidenceIds.filter(id=>id!==s.evidenceId)})}/>{s.evidenceId} · {s.title}<code>{s.sha256}</code></label>):<p>本案暂无允许绑定的证据登记，不能提交预览。请先完成真实来源登记。</p>}</fieldset>
 <label><input type="checkbox" checked={confirmed} onChange={e=>{clear();setConfirmed(e.target.checked)}}/>我理解这是人工录入的未核验时段，仅作固定休息基线技术预览，不作法律或责任判定</label><button type="button" disabled={!confirmed||busy||!sources.length||sourceStale} onClick={()=>void calculate()}>{busy?'核心计算中…':'运行技术预览（不保存）'}</button>{busy&&<p role="status">正在请求真实计算核心，编辑输入会停止等待并清空旧结果。</p>}{message&&<p role="alert">{message}</p>}{preview&&<RestResult preview={preview}/>}</div>
}

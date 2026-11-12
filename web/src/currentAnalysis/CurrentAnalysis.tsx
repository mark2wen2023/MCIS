import {useEffect,useRef,useState} from 'react'
import type { EChartsOption } from 'echarts'
import {Link} from 'react-router-dom'
import {getRole,getOperator,onIdentityChange,ApiError} from '../api'
import {caseIdentity} from '../cases/identity'
import {onTrackNavigation} from '../tracks/navigation'
import {readError} from '../tracks/api'
import {trackQuery,provenanceLabels,plotIndices,TrackDataError,type Snapshot} from '../tracks/model'
import {EChart} from '../components/EChart'
import {ASSUMPTIONS,COVERAGE,parseMetadata,parseResult,type Result} from './model'
import '../styles/w12-current.css'

async function get(path:string,signal:AbortSignal){
 const res=await fetch('/api/v1'+path,{signal,cache:'no-store',headers:{'X-MCIS-Role':getRole(),'X-MCIS-Operator':encodeURIComponent(getOperator())}})
 const raw:unknown=await res.json();if(!res.ok){const e=raw as {code?:string;message?:string};throw new ApiError(res.status,e.code??'HTTP_'+res.status,e.message??'读取失败',null)}return raw
}
function message(e:unknown){if(e instanceof TrackDataError)return readError(e);if(e instanceof SyntaxError)return '服务返回格式无法解析，未显示结果。';if(e instanceof TypeError)return '无法连接或读取服务，未显示旧结果。';if(e instanceof ApiError&&e.status===403)return '当前身份无权读取此案航迹，先前结果已清除。';return e instanceof Error?e.message:'读取失败，未显示旧结果。'}
export function CurrentAnalysis({caseId,who}:{caseId:string;who:string}){
 const [meta,setMeta]=useState<Snapshot|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(true)
 const [own,setOwn]=useState(''),[target,setTarget]=useState(''),[from,setFrom]=useState(''),[to,setTo]=useState('')
 const [result,setResult]=useState<Result|null>(null),[revision,setRevision]=useState(0)
 const controller=useRef<AbortController|null>(null),generation=useRef(0),pending=useRef(true)
 const invalidate=()=>{generation.current++;controller.current?.abort();pending.current=false;setResult(null);setBusy(false)}
 useEffect(()=>{
  const a=new AbortController();controller.current=a;const id=++generation.current;pending.current=true;setBusy(true);setMeta(null);setError('')
  const cancel=()=>{generation.current++;controller.current?.abort();pending.current=false;setResult(null);setMeta(null);setBusy(false);setError('导航或身份已变化，请重新读取本案。')}
  const off=onIdentityChange(cancel),nav=onTrackNavigation(cancel)
  Promise.all([get('/cases/'+encodeURIComponent(caseId),a.signal),get('/cases/'+encodeURIComponent(caseId)+'/vessels',a.signal)]).then(([c,v])=>{
   if(!a.signal.aborted&&id===generation.current&&caseIdentity()===who){const m=parseMetadata(caseId,c,v);setMeta(m);setOwn('');setTarget('')}
  }).catch(e=>{if(!a.signal.aborted&&id===generation.current)setError(message(e))}).finally(()=>{if(id===generation.current){pending.current=false;setBusy(false)}})
  // Intentionally abort the latest request owned by this session, including a later CPA request.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return()=>{generation.current++;controller.current?.abort();off();nav()}
 },[caseId,who,revision])
 const changed=(setter:(s:string)=>void,value:string)=>{invalidate();setError('');setter(value)}
 const calculate=async()=>{
  if(pending.current||caseIdentity()!==who||!meta)return
  invalidate();setError('')
  try{
   if(!own||!target||own===target)throw Error('请明确选择本案两艘不同船舶。')
   const q=new URLSearchParams(trackQuery(from,to).replace(/^\?/,''));q.set('ownVesselId',own);q.set('targetVesselId',target)
   const start=q.has('fromSec')?Number(q.get('fromSec')):null,end=q.has('toSec')?Number(q.get('toSec')):null
   const a=new AbortController();controller.current=a;const id=++generation.current;pending.current=true;setBusy(true)
   try{const raw=await get('/cases/'+encodeURIComponent(caseId)+'/analysis/current?'+q,a.signal)
    if(!a.signal.aborted&&id===generation.current&&caseIdentity()===who)setResult(parseResult(raw,caseId,own,target,start,end))
   }catch(e){if(!a.signal.aborted&&id===generation.current)setError(message(e))}
   finally{if(id===generation.current){pending.current=false;setBusy(false)}}
  }catch(e){setError(message(e))}
 }
 return <section className="w122-page"><header className="w122-head"><div><span className="w122-kicker">CURRENT CASE · SAVED POINTS</span><h1>当前案件 · 同刻点 CPA 分析</h1><p>{meta?.case.title??caseId} · {meta?.case.isFictionalDemo?'示例数据（虚构）':'非虚构标记不等于资料已核验'}</p></div><Link to={'/track?case='+encodeURIComponent(caseId)}>核对本案已保存航迹 →</Link></header>
  <p className="w122-notice">仅作安全调查技术分析，不作责任认定或安全结论。这里读取当前案件库，不读取固定演示曲线；旧基准在下方独立入口。</p>
  <p>{ASSUMPTIONS}</p><p>{COVERAGE}</p>
  <form className="w122-controls" onSubmit={e=>{e.preventDefault();void calculate()}}>
   <label>本船<select value={own} onChange={e=>changed(setOwn,e.target.value)} disabled={!meta}><option value="">请选择本船</option>{meta?.vessels.map(v=><option key={v.vesselId} value={v.vesselId}>{v.name} · {v.vesselId}</option>)}</select></label>
   <label>目标船<select value={target} onChange={e=>changed(setTarget,e.target.value)} disabled={!meta}><option value="">请选择目标船</option>{meta?.vessels.map(v=><option key={v.vesselId} value={v.vesselId}>{v.name} · {v.vesselId}</option>)}</select></label>
   <label>起始相对秒<input value={from} onChange={e=>changed(setFrom,e.target.value)} placeholder="全部已存范围"/></label>
   <label>结束相对秒<input value={to} onChange={e=>changed(setTo,e.target.value)} placeholder="全部已存范围"/></label>
   <button disabled={busy||!meta||!own||!target||own===target} type="submit">{busy?'正在读取 / 计算…':'计算同刻已存点'}</button>
   <button type="button" disabled={busy} onClick={()=>{invalidate();setRevision(n=>n+1)}}>重新读取本案</button>
  </form>
  <p className="w122-muted">时间相对案件 UTC 纪元：{meta?.case.caseEpochUtc??'尚未读取'}。每船最多 5000 点；超限请缩小窗口。局部原点纬度 ±85°以内、点距原点不超过100km，仅为工程适用域，不是精度或安全保证。输入更改会清除旧结果。</p>
  {busy&&<p role="status">正在读取或计算，未显示旧结果…</p>}{error&&<p role="alert" className="w122-error">{error}</p>}
  {meta&&meta.vessels.length<2&&<p role="status">本案不足两艘已登记船舶。先登记船舶并保存航迹，不会回退到虚构案例。</p>}
  {result&&<CurrentResult key={result.inputDigest} result={result}/>}
 </section>
}
const fmt=(n:number|null)=>n===null?'不适用':n.toFixed(4)
export function CurrentResult({result:r,charts=true}:{result:Result;charts?:boolean}){
 const [page,setPage]=useState(0),total=Math.max(1,Math.ceil(r.rows.length/100)),current=Math.min(page,total-1)
 const plotted=plotIndices(r.rows.length).map(i=>r.rows[i]!)
 const source=(p:Result['rows'][number]['own'])=><><b>{provenanceLabels[p.provenance??'Unknown']}</b><br/>{p.source?.trim()||'来源标签未提供'}</>
 const option:EChartsOption={tooltip:{trigger:'item',renderMode:'richText'},legend:{data:['点位间距【推算】','DCPA【推算】','TCPA【推算】']},grid:{left:70,right:75,bottom:65,top:50},xAxis:{type:'value',name:'相对秒',nameLocation:'middle',nameGap:30},yAxis:[{type:'value',name:'nm',scale:true},{type:'value',name:'min（有符号）',scale:true}],series:[{name:'点位间距【推算】',type:'scatter',symbolSize:5,data:plotted.map(x=>[x.timeSec,x.currentDistanceNm])},{name:'DCPA【推算】',type:'scatter',symbolSize:5,data:plotted.map(x=>[x.timeSec,x.dcpaNm])},{name:'TCPA【推算】',type:'scatter',symbolSize:5,yAxisIndex:1,data:plotted.filter(x=>x.tcpaMin!==null).map(x=>[x.timeSec,x.tcpaMin])}]}
 return <section className="w122-result" aria-label="当前案计算结果"><h2>已存输入的瞬时模型结果 · 【推算】</h2><div className="w122-stats"><div><strong>{r.counts.matched}</strong> 同刻配对</div><div><strong>{r.counts.own} / {r.counts.target}</strong> 本船 / 目标船已存点</div><div><strong>{r.counts.unmatchedOwn} / {r.counts.unmatchedTarget}</strong> 未配对点（不计算）</div></div>
  {r.rows.length===0?<p role="status">此窗口没有可配对同刻点（包括无航迹情形）。未调用计算核心，也没有插值补齐。</p>:<>{charts&&<EChart option={option} height={340}/>}<p>仅绘制离散样点，不连接、不平滑。图中 {plotted.length} / {r.rows.length} 个配对点{plotted.length<r.rows.length?'（均匀展示抽样；下方分页仍含全部计算点）':''}。TCPA &lt; 0：该瞬时模型的最近会遇已过去；相对静止时 TCPA 不适用（非零、非安全结论）。核心保留6位小数；显示为0不能用于精确判定最近会遇时刻。</p>
  <div className="w122-table"><table><thead><tr><th>相对秒 / UTC</th><th>点位间距 nm</th><th>DCPA nm</th><th>TCPA min</th><th>本船输入来源</th><th>目标船输入来源</th><th>已存输入核对</th></tr></thead><tbody>{r.rows.slice(current*100,(current+1)*100).map(x=><tr key={x.timeSec}><td>{x.timeSec}<br/>{x.utc}</td><td>{fmt(x.currentDistanceNm)}</td><td>{fmt(x.dcpaNm)}</td><td>{fmt(x.tcpaMin)}{x.isDegenerate&&<small>（相对静止）</small>}{x.isDiverging&&x.tcpaMin===0&&<small>（核心标记已远离，时间舍入为0）</small>}</td><td>{source(x.own)}</td><td>{source(x.target)}</td><td><details><summary>两船点位与 SOG/COG</summary>{[x.own,x.target].map(p=><p key={p.vesselId}>{p.vesselId}<br/>纬度 {p.latDeg}° / 经度 {p.lonDeg}°<br/>SOG {p.sogKn} kn / COG {p.cogDeg}°<br/>{p.utc}</p>)}</details></td></tr>)}</tbody></table></div>
  <nav aria-label="结果分页"><button disabled={current===0} onClick={()=>setPage(current-1)}>上一页</button><span> {current+1} / {total} 页 · 每页100点 </span><button disabled={current+1>=total} onClick={()=>setPage(current+1)}>下一页</button></nav></>}
  <details className="w122-provenance"><summary>输入标识、计算假设与可追溯边界</summary><p>{ASSUMPTIONS}</p><p>{COVERAGE}</p><p>案件 {r.caseId} · 案件纪元 {r.caseEpochUtc} · 两船 {r.vessels.map(v=>v.vesselId).join(' / ')}</p><p>ENU 原点：{r.origin.latDeg}°, {r.origin.lonDeg}° · 核心：{r.coreVersion??'未调用'}</p><p>本次输入摘要：{r.inputDigest}</p><p>摘要只标识本次已存计算输入，不是证据签名、真实性认证或长期快照。返回前已重检输入和访问权限；之后源数据仍可能变化。时间质量、测量不确定度与位置参考点未提供。</p></details>
 </section>
}

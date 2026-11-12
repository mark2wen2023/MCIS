import { useMemo, useState } from 'react'
import { describe, PAGE_SIZE, plotIndices, provenanceLabels, type Snapshot, type TrackPoint } from './model'

function Plot({points,selected,onSelect}:{points:TrackPoint[];selected:number|null;onSelect:(n:number)=>void}) {
  const indices=useMemo(()=>plotIndices(points.length),[points])
  const bounds=useMemo(()=>{
    let minX=180,maxX=-180,minY=90,maxY=-90
    for(const p of points){minX=Math.min(minX,p.lonDeg);maxX=Math.max(maxX,p.lonDeg);minY=Math.min(minY,p.latDeg);maxY=Math.max(maxY,p.latDeg)}
    if(minX===maxX){minX=Math.max(-180,minX-.001);maxX=Math.min(180,maxX+.001)}if(minY===maxY){minY=Math.max(-90,minY-.001);maxY=Math.min(90,maxY+.001)}
    return {minX,maxX,minY,maxY}
  },[points])
  if(!points.length)return <p>当前筛选没有点，未绘制航迹。</p>
  const x=(p:TrackPoint)=>64+(p.lonDeg-bounds.minX)/(bounds.maxX-bounds.minX)*700
  const y=(p:TrackPoint)=>320-(p.latDeg-bounds.minY)/(bounds.maxY-bounds.minY)*280
  const selectedPoint=selected===null?undefined:points[selected]
  return <div className="w10-plot">
    <svg viewBox="0 0 820 380" role="img" aria-label="经纬度散点示意，可在下方数据表选择同一航迹点">
      <path d="M64 40V320H764" fill="none" stroke="#7894a9"/>
      {[0,.25,.5,.75,1].map(n=><g key={n}><path d={`M64 ${320-n*280}H764`} stroke="#2d465b"/><text x="58" y={324-n*280} textAnchor="end">{(bounds.minY+n*(bounds.maxY-bounds.minY)).toFixed(4)}</text><text x={64+n*700} y="343" textAnchor="middle">{(bounds.minX+n*(bounds.maxX-bounds.minX)).toFixed(4)}</text></g>)}
      <text x="414" y="371" textAnchor="middle">经度（°）</text><text x="66" y="24">纬度（°）</text>
      <g aria-hidden="true">{indices.map(i=><circle key={i} cx={x(points[i]!)} cy={y(points[i]!)} r="3.5" fill="#6bd3e6" onClick={()=>onSelect(i)}><title>{`第${i+1}点 · T${points[i]!.timeSec}s`}</title></circle>)}{selectedPoint&&<circle cx={x(selectedPoint)} cy={y(selectedPoint)} r="8" fill="none" stroke="#ffd580" strokeWidth="3"/>}</g>
    </svg>
    <p>仅点位示意，非 ENC 或等距地图；不连接航线、不插值、不用于量距或航行。可点击圆点，也可用下方列表按钮选点。</p>
    <p>显示 {indices.length} / {points.length} 点{indices.length<points.length?'：按索引均匀选择已存点用于绘图，未重采样轨迹；数据表保留全部筛选结果。':'，无绘图抽样。'}</p>
  </div>
}
function PointDetail({point,index}:{point:TrackPoint;index:number}){
  return <section className="w10-detail" aria-label="选中点详情"><h3>选中第 {index+1} 点</h3><dl><dt>UTC</dt><dd>{point.utc}</dd><dt>相对时间</dt><dd>{point.timeSec} s</dd><dt>经纬度</dt><dd>{point.lonDeg}° / {point.latDeg}°</dd><dt>SOG / COG</dt><dd>{point.sogKn} kn / {point.cogDeg}°</dd><dt>船首向 HDG</dt><dd>{point.hdgDeg==null?'未提供':point.hdgDeg+'°'}</dd><dt>转向率 ROT</dt><dd>{point.rotDegPerMin==null?'未提供':point.rotDegPerMin+'°/min'}</dd><dt>来源类型记录</dt><dd>{provenanceLabels[point.provenance??'Unknown']}</dd><dt>来源标签</dt><dd>{point.source?.trim()||'未登记来源标签'}</dd></dl></section>
}
function VesselTrack({points}:{points:TrackPoint[]}){
  const [filter,setFilter]=useState('all'),[page,setPage]=useState(0),[selected,setSelected]=useState<number|null>(null)
  const stats=useMemo(()=>describe(points),[points])
  const filtered=useMemo(()=>filter==='all'?points:points.filter(p=>(p.provenance??'Unknown')===filter),[points,filter])
  const pageCount=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE)),safePage=Math.min(page,pageCount-1)
  const rows=filtered.slice(safePage*PAGE_SIZE,(safePage+1)*PAGE_SIZE)
  const select=(i:number)=>{setSelected(i);setPage(Math.floor(i/PAGE_SIZE))}
  return <>
    <div className="w10-stats"><div><strong>{stats.count}</strong>已存点</div><div><strong>{stats.minTime??'—'} / {stats.maxTime??'—'}</strong>时间范围（相对秒）</div><div><strong>{stats.maxInterval??'—'}</strong>最大相邻正时间间隔（秒）</div><div><strong>{stats.missingSource}</strong>缺少来源标签</div></div>
    <p className="w10-notice">最大间隔只是本次返回数据的描述，不自动判定缺口或异常。时间质量、清洗结果及剔除清单：接口未提供。来源标签和类型只是数据库记录，不证明证据完整或可信。</p>
    {(stats.duplicateTimes>0||stats.reversedTimes>0)&&<p className="w10-warning" role="status">返回顺序中有 {stats.duplicateTimes} 对相邻同时间点、{stats.reversedTimes} 对时间倒退。按返回顺序显示，没有排序修复、剔除或保存。</p>}
    {stats.spansDateline&&<p className="w10-warning">经度跨度超过180°，可能跨越日期线。此坐标散点不作连续海图，不能据图判断绕行距离。</p>}
    <div className="w10-provenance">{Object.entries(stats.provenance).map(([key,count])=><span key={key}>{provenanceLabels[key as keyof typeof provenanceLabels]}：{count}</span>)}</div>
    <label className="w10-filter">筛选来源类型<select value={filter} onChange={e=>{setFilter(e.target.value);setSelected(null);setPage(0)}}><option value="all">全部已存点</option>{Object.entries(provenanceLabels).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
    {points.length===0?<p role="status">本船没有已保存航迹点。新增船舶不会自动生成航迹；本页未开放导入。</p>:<>
      <div className="w10-chart-detail"><section><h3>点位分布 · 当前筛选 {filtered.length} 点</h3><Plot points={filtered} selected={selected} onSelect={select}/></section>{selected!==null&&filtered[selected]?<PointDetail point={filtered[selected]} index={selected}/>:<p className="w10-detail">选择图中点或下方“查看点”按钮查看精确记录。</p>}</div>
      <div className="w10-table-scroll" tabIndex={0} role="region" aria-label="航迹点数据表，可横向滚动"><table><caption>已存点时序 · 按服务返回顺序 · 时间为 UTC</caption><thead><tr><th scope="col">点</th><th scope="col">T（s）</th><th scope="col">UTC</th><th scope="col">经度 / 纬度（°）</th><th scope="col">SOG（kn）/ COG（°）</th><th scope="col">类型 / 来源标签</th></tr></thead><tbody>{rows.map((p,i)=>{const n=safePage*PAGE_SIZE+i;return <tr key={n} className={n===selected?'w10-selected':''}><td><button type="button" aria-pressed={n===selected} onClick={()=>select(n)} aria-label={'查看点 '+(n+1)}>{n+1}</button></td><td>{p.timeSec}</td><td>{p.utc}</td><td>{p.lonDeg} / {p.latDeg}</td><td>{p.sogKn} / {p.cogDeg}</td><td>{provenanceLabels[p.provenance??'Unknown']}<small>{p.source?.trim()||'未登记来源标签'}</small></td></tr>})}</tbody></table></div>
      {filtered.length===0&&<p role="status">此来源类型没有航迹点；请更换筛选。</p>}
      <div className="w10-pagination"><button type="button" disabled={safePage===0} onClick={()=>setPage(p=>Math.max(0,p-1))}>上一页</button><span aria-live="polite">第 {safePage+1} / {pageCount} 页 · {filtered.length} 点 · 每页 {PAGE_SIZE} 点</span><button type="button" disabled={safePage>=pageCount-1} onClick={()=>setPage(p=>p+1)}>下一页</button></div>
    </>}
  </>
}
export function TrackView({snapshot}:{snapshot:Snapshot}){
  const choices=useMemo(()=>{
    const map=new Map(snapshot.vessels.map(v=>[v.vesselId,{...v,registered:true}]))
    for(const t of snapshot.tracks)if(!map.has(t.vesselId))map.set(t.vesselId,{vesselId:t.vesselId,name:'未登记船舶',registered:false})
    return [...map.values()]
  },[snapshot])
  const [selection,setSelection]=useState(choices[0]?.vesselId??'')
  const vessel=choices.find(v=>v.vesselId===selection)
  const points=snapshot.tracks.find(t=>t.vesselId===selection)?.points??[]
  return <><div className="w10-case"><span>{snapshot.case.isFictionalDemo?'虚构演示':'非虚构案件'}</span><h2>{snapshot.case.title}</h2><p>{snapshot.case.caseId} · 时间纪元（UTC）：{snapshot.case.caseEpochUtc}</p></div>
    {!choices.length?<p role="status">本案没有船舶或已保存航迹。请先到船舶参数页登记；本页不会自动生成航迹。</p>:<><label className="w10-filter">选择船舶<select value={selection} onChange={e=>setSelection(e.target.value)}>{choices.map(v=><option key={v.vesselId} value={v.vesselId}>{v.name} · {v.vesselId}</option>)}</select></label>{vessel&&!vessel.registered&&<p className="w10-warning">此航迹桶没有对应船舶登记信息。保留已存数据展示，不推断船名或船型。</p>}<VesselTrack key={selection} points={points}/></>}
  </>
}

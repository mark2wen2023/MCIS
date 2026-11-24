import { useId } from 'react'

// Component input only; this is not a storage or transport contract.
const levels = [
  ['Government', '政府与法规'], ['Regulatory', '监管'], ['Company', '公司'],
  ['ShipManagement', '船舶管理'], ['CrewActs', '船员行为'], ['EquipmentEnvironment', '设备与环境'],
] as const
type Level = typeof levels[number][0]
type DraftNode = { id: string; label: string; level: Level }
type Link = { fromId: string; toId: string }
const hasId = (id: string) => id.trim().length !== 0
export type SyntheticAcciMapDraft = {
  caseId: string
  isFictionalDemo: true
  nodes: readonly DraftNode[]
  edges: readonly Link[]
  informationFlows: readonly Link[]
}

export function AcciMapDraftDiagram({ caseId, draft }: { caseId: string; draft: SyntheticAcciMapDraft }) {
  const id = useId()
  if (!caseId || !draft.isFictionalDemo || draft.caseId !== caseId)
    return <p role="status">草图不可预览：仅支持当前合成案。</p>

  const index = new Map<string, { x: number; y: number } | null>()
  const lanes = levels.map(([level, label], i) => {
    const y = 74 + i * 104
    const nodes = draft.nodes.filter(n => n.level === level).map((node, j) => {
      const point = { x: 170 + j * 192, y: y + 15 }
      // A visible, not-yet-numbered row is never a valid link endpoint.
      if (hasId(node.id)) index.set(node.id, index.has(node.id) ? null : point)
      return { node, ...point }
    })
    return { label, y, nodes }
  })
  const width = Math.max(760, 170 + Math.max(0, ...lanes.map(lane => lane.nodes.length)) * 192)
  const links = [
    ...draft.edges.map(link => ({ ...link, kind: 'relation' as const })),
    ...draft.informationFlows.map(link => ({ ...link, kind: 'information' as const })),
  ]
  const endpoints = (link: Link) => {
    const start = index.get(link.fromId), end = index.get(link.toId)
    return start && end && link.fromId !== link.toId ? { start, end } : null
  }
  const drawable = links.flatMap(link => {
    const points = endpoints(link)
    return points ? [{ ...link, ...points }] : []
  })
  const omitted = links.length - drawable.length
  // Assign a distinct track to each line between an unordered endpoint pair.
  // The same canonical perpendicular is used for either direction.
  const pairs = new Map<string, typeof drawable>()
  for (const link of drawable) {
    const pair = JSON.stringify([link.fromId, link.toId].sort())
    const group = pairs.get(pair)
    if (group) group.push(link)
    else pairs.set(pair, [link])
  }
  const trackByLink = new Map<typeof drawable[number], number>()
  for (const group of pairs.values())
    group.forEach((link, i) => trackByLink.set(link, (i - (group.length - 1) / 2) * 10))

  return <figure>
    <figcaption>AcciMap 合成草图 · 待核验 · 证据状态未知。实线为输入关系，虚线为输入信息流；都不是已证实因果。</figcaption>
    <div style={{ overflowX: 'auto' }}>
      <svg role="img" aria-labelledby={`${id}-title ${id}-desc`} viewBox={`0 0 ${width} 754`} style={{ minWidth: width }}>
        <title id={`${id}-title`}>AcciMap 六层人工草图 · 待核验</title>
        <desc id={`${id}-desc`}>只展示明确输入，不补节点或边、不验证来源与因果。无法连到唯一端点或自连的边不绘制。全部输入连线可在图下文字清单核对。</desc>
        <defs>
          <marker id={`${id}-arrow`} markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto">
            <path d="M0 0 L6 3 L0 6" fill="#465f72"/>
          </marker>
        </defs>
        <rect width={width} height="754" fill="#fff"/>
        <text x="18" y="29" fill="#203c4a" fontSize="18">AcciMap 合成草图 · 待核验 · 证据状态未知</text>
        <text x="18" y="54" fill="#203c4a" fontSize="13">实线：输入关系　虚线：输入信息流　均非已证实因果；不核验来源</text>
        {lanes.map(({ label, y }) => <g key={label}>
          <rect x="10" y={y} width={width - 20} height="96" rx="4" fill="#edf4f7"/>
          <text x="22" y={y + 29} fill="#203c4a" fontSize="16">{label}</text>
        </g>)}
        {drawable.map((link, i) => {
          const { start, end, kind, fromId, toId } = link
          const down = end.y > start.y
          const same = start.y === end.y
          const x1 = same ? (start.x < end.x ? start.x + 158 : start.x) : start.x + 79
          const x2 = same ? (start.x < end.x ? end.x : end.x + 158) : end.x + 79
          const y1 = start.y + (same ? 32 : down ? 64 : 0)
          const y2 = end.y + (same ? 32 : down ? 0 : 64)
          const span = Math.hypot(x2 - x1, y2 - y1)
          const signedTrack = trackByLink.get(link)! * (fromId < toId ? 1 : -1)
          const dx = -(y2 - y1) / span * signedTrack, dy = (x2 - x1) / span * signedTrack
          return <line key={i} x1={x1 + dx} x2={x2 + dx} y1={y1 + dy} y2={y2 + dy} stroke="#465f72"
            strokeDasharray={kind === 'information' ? '5 4' : undefined} markerEnd={`url(#${id}-arrow)`}/>
        })}
        {lanes.flatMap(({ nodes }) => nodes.map(({ node, x, y }, i) => <g key={`${node.level}:${i}`}>
          <title>{`${node.id} · ${node.label} · 待核验 · 证据状态未知`}</title>
          <rect x={x} y={y} width="158" height="64" rx="5" fill="#fff" stroke="#547286"/>
          <text x={x + 7} y={y + 18} fill="#203c4a" fontSize="13">{node.id.slice(0, 19)}</text>
          <text x={x + 7} y={y + 37} fill="#203c4a" fontSize="13">{node.label.slice(0, 10)}</text>
          <text x={x + 7} y={y + 55} fill="#203c4a" fontSize="12">待核验 · 证据状态未知</text>
        </g>))}
        <text x="18" y="724" fill="#203c4a" fontSize="13">未绘制连线 {omitted} 条（端点缺失、歧义或自连）；完整节点 ID 见节点标题。</text>
      </svg>
    </div>
    <details>
      <summary>查看全部输入连线（含未绘制项）</summary>
      {links.length ? <ol>{links.map((link, i) => {
        const drawn = endpoints(link) !== null
        return <li key={i}>{link.kind === 'information' ? '输入信息流' : '输入关系'}：{hasId(link.fromId) ? link.fromId : '缺失'} → {hasId(link.toId) ? link.toId : '缺失'}{drawn ? '（图中已绘）' : '（未绘制）'}</li>
      })}</ol> : <p>无输入连线。</p>}
    </details>
  </figure>
}

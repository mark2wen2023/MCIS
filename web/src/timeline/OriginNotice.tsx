import type {TimelineEvent} from '../types'
export type EventOrigins = Record<string, {status: 'unavailable' | 'restored-history'; sourcePackageSha256?: string; rowSha256?: string}>
const sha = (s: unknown) => typeof s === 'string' && /^[a-f0-9]{64}$/.test(s)
export function OriginNotice({caseId, events, origins}: {caseId: string; events: (TimelineEvent & {caseId?: string})[]; origins?: EventOrigins}) {
  return <div aria-label="时间线声明来源">
    <p>confirmed / presumptive 是记录声明，不代表本次人工复核；当前接口不提供新复核证明。</p>
    <ul>{events.map(event => {
      const origin = origins?.[event.eventId]
      const restored = event.caseId === caseId && origin?.status === 'restored-history' && sha(origin.sourcePackageSha256) && sha(origin.rowSha256)
      return <li key={event.eventId}>{event.eventId} · {event.title}：{restored
        ? <>恢复的历史声明 · 最近导入包 <code style={{overflowWrap: 'anywhere'}}>{origin.sourcePackageSha256}</code> · 非本次批准</>
        : '恢复来源未提供；不据此判断为新建或已复核'}</li>
    })}</ul>
  </div>
}

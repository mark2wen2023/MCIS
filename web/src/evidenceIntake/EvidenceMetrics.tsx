import { Metric } from '../components/Panel'
import type { EvidenceItem } from '../types'

type CountedEvidence = Pick<EvidenceItem, 'status' | 'needsReview' | 'confidentiality'>
/** Counts describe only a successfully read list, not unread or denied evidence. */
export function EvidenceMetrics({ data, error }: { data: readonly CountedEvidence[] | null; error: string | null }) {
  if (error !== null || data === null) {
    const value = error !== null ? '不可用' : '待载入'
    return <>{['证据条目', '哈希校验一致', '需复核', '受限（保密）'].map(label =>
      <Metric key={label} label={label} value={value} />)}</>
  }
  return <>
    <Metric label="证据条目" value={data.length} unit="条" />
    <Metric label="哈希校验一致" value={data.filter(e => e.status === 'Verified').length} unit={`/ ${data.length}`} tone="green" />
    <Metric label="需复核" value={data.filter(e => e.needsReview).length} unit="条" tone="amber" />
    <Metric label="受限（保密）" value={data.filter(e => e.confidentiality === 'Restricted').length} unit="条" tone="pur" />
  </>
}

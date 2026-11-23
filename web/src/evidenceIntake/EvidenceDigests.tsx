import type { EvidenceItem } from '../types'

/** Read-only labels for the existing registration and custody-derived fields. */
export function EvidenceDigests({ item }: { item: Pick<EvidenceItem, 'sha256' | 'currentSha256'> }) {
  return <>
    <dt>登记原始 SHA-256</dt><dd className="mono" style={{ overflowWrap: 'anywhere' }}>{item.sha256 || '未提供'}</dd>
    <dt>保管链当前 SHA-256</dt><dd className="mono" style={{ overflowWrap: 'anywhere' }}>{item.currentSha256 || '未提供'}</dd>
    <dt>摘要口径</dt><dd>当前摘要由登记及保管链 Change 事件推导，不是解析修订号。摘要本身不证明内容真实性；本处不展示解析结果版本。</dd>
  </>
}

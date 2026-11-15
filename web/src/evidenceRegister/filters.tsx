import type { EvidenceItem } from '../types'

export interface RegisterFilter { query: string; status: EvidenceItem['status'] | ''; needsReview: boolean }
export const EMPTY_FILTER: RegisterFilter = { query: '', status: '', needsReview: false }
export function filterEvidence(items: readonly EvidenceItem[], filter: RegisterFilter): EvidenceItem[] {
  const query = filter.query.trim().toLowerCase()
  return items.filter(item => (!filter.status || item.status === filter.status)
    && (!filter.needsReview || item.needsReview === true)
    && (!query || [item.evidenceId, item.title, item.source, item.extractedBy]
      .some(value => typeof value === 'string' && value.toLowerCase().includes(query))))
}

export function RegisterFilters({ value, onChange, count, total, ready, hiddenSelection }: {
  value: RegisterFilter; onChange: (next: RegisterFilter) => void; count: number; total: number;
  ready: boolean; hiddenSelection?: string;
}) {
  return <div style={{ padding: 12 }}>
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'end' }}>
      <label>查找证据<input className="input" type="search" maxLength={200} disabled={!ready}
        placeholder="编号、标题、来源或提取人" value={value.query}
        onChange={event => onChange({ ...value, query: event.target.value })} /></label>
      <label>哈希状态<select className="select" disabled={!ready} value={value.status}
        onChange={event => onChange({ ...value, status: event.target.value as RegisterFilter['status'] })}>
        <option value="">全部状态</option><option value="Unverified">未校验</option>
        <option value="Verified">哈希一致</option><option value="Mismatch">哈希不一致</option>
        <option value="NeedsReview">状态为需复核</option>
      </select></label>
      <label><input type="checkbox" disabled={!ready} checked={value.needsReview}
        onChange={event => onChange({ ...value, needsReview: event.target.checked })} />仅看标注需复核</label>
      <button type="button" className="btn btn-sm" disabled={!ready || (!value.query && !value.status && !value.needsReview)}
        onClick={() => onChange({ ...EMPTY_FILTER })}>清除筛选</button>
    </div>
    <p className="p6-note" role="status">{ready ? `显示 ${count} / ${total} 条证据。` : '证据清单尚未加载。'}仅筛选当前清单的元数据，不检索原件内容。</p>
    {hiddenSelection && <p className="p6-note">当前选中 {hiddenSelection} 不在筛选结果中，右侧保管链仍对应该证据；未自动切换选择。</p>}
  </div>
}

/** Display returned declarations only. A reference/hash is not proof of preserved bytes. */
export function SourceDisclosure({ caseId, evidenceId, sourceSha256 }: {
  caseId: string; evidenceId?: string | null; sourceSha256?: string | null;
}) {
  const hasId = typeof evidenceId === 'string' && evidenceId.trim().length > 0
  const validId = hasId && /^EV-\d+$/.test(evidenceId!)
  const hasHash = typeof sourceSha256 === 'string' && sourceSha256.trim().length > 0
  const validHash = hasHash && /^[a-fA-F0-9]{64}$/.test(sourceSha256!)
  const href = validId && caseId.trim() ? '#/evidence?' + new URLSearchParams({ case: caseId, id: evidenceId! }).toString() : null
  return <aside aria-label="笔录来源记录" className="p6-note" data-testid="interview-source-disclosure">
    <b>笔录来源记录 · 待人工核对</b>
    <p>{!hasId ? '当前返回记录未提供原件证据编号；不能据此认定已保全原件。' :
      <>记录的证据编号：<span>{evidenceId}</span>。{href ? <a href={href}>打开本案证据清单核对</a> : '编号或案件信息不完整，未生成证据链接。'}</>}</p>
    <p>{!hasHash ? '当前返回记录未提供来源 SHA-256。' : !validHash ? '来源 SHA-256 格式异常，暂不能用于摘要核对。' :
      <>记录的来源 SHA-256：<span className="mono" style={{ overflowWrap: 'anywhere' }}>{sourceSha256}</span></>}</p>
    <p>以上仅为笔录中记录的来源元数据；未读取或核验原件，不证明来源真实或内容一致，也不代表 OCR/AI 已解析。字段未返回不等于原始资料不存在。</p>
  </aside>
}

import type { Citation } from './types'
import index from './publicTextIndex.json'

/** Exact declared line interval, not a quote search or evidence authenticity check. */
export function publicTextLocation(citation: Citation, caseId: string) {
  if (caseId !== index.caseId || citation.kind !== 'evidence' || citation.id !== index.evidenceId
      || citation.registration !== 'registered' || citation.unregistered) return null
  // Only the existing case-scoped evidence route qualifies; no external href supplied by data is followed here.
  if (typeof citation.href !== 'string' || typeof citation.sourceRef !== 'string') return null
  const parts = citation.href.split('?')
  if (parts.length !== 2) return null
  const [route, query] = parts
  if (route !== '#/evidence' || !query) return null
  const params = new URLSearchParams(query)
  if (params.getAll('case').length !== 1 || params.get('case') !== caseId
      || params.getAll('id').length !== 1 || params.get('id') !== index.evidenceId
      || [...params.keys()].some(key => key !== 'case' && key !== 'id')) return null
  const match = /^reports\/yangze22\/report\.txt#L([1-9]\d*)-L([1-9]\d*); SHA256=([0-9a-f]{64}); PDF页=([1-9]\d*)–([1-9]\d*); 正文页=([1-9]\d*)–([1-9]\d*)$/.exec(citation.sourceRef || '')
  if (!match || match[0] !== citation.sourceRef || match[3] !== index.sha256) return null
  const [start, end, pageStart, pageEnd, printedStart, printedEnd] = [match[1], match[2], match[4], match[5], match[6], match[7]].map(Number)
  if (![start, end, pageStart, pageEnd, printedStart, printedEnd].every(Number.isSafeInteger)
      || start > end || end > index.lineCount) return null
  const pageAt = (line: number) => 1 + index.pageBreakLines.filter(boundary => boundary <= line).length
  if (pageStart !== pageAt(start) || pageEnd !== pageAt(end)
      || printedStart !== pageStart - 2 || printedEnd !== pageEnd - 2) return null
  return { start, end, pageStart, pageEnd, sha256: index.sha256,
    href: `https://github.com/mark2wen2023/MCIS/blob/${index.commit}/${index.path}#L${start}-L${end}` }
}

export function PublicTextLocation({ citation, caseId }: { citation: Citation; caseId: string }) {
  const location = publicTextLocation(citation, caseId)
  if (!location) return null
  return <span className="p6-note"> · <a href={location.href} target="_blank" rel="noopener noreferrer"
    title={`固定公开文本 SHA256=${location.sha256}；不是当前证据原件核验；不是 PDF 跳页`}>
    固定版本公开文本 L{location.start}–L{location.end}</a>（外部 GitHub；需核对原文，非 PDF 跳页）</span>
}

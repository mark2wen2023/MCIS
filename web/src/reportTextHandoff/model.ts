import { parseReceipt, type Receipt } from '../evidenceIntake/model'

export function publicSource(value: string): string {
  if (typeof value !== 'string' || value.length > 2000 || value !== value.trim() || /[\s\\\u0000-\u001f\u007f]/.test(value)) throw Error('请填写不含空白的公开来源 HTTPS 地址。')
  let url: URL
  try { url = new URL(value) } catch { throw Error('请填写完整的公开来源 HTTPS 地址。') }
  if (!value.startsWith('https://') || url.protocol !== 'https:' || !url.hostname || url.username || url.password) throw Error('来源须为无账号口令的 HTTPS 地址；本页不会访问或认证该地址。')
  return value
}

export function textHandoff(receipt: Receipt, sourceUrl: string, declaredPublic: boolean) {
  const r = parseReceipt(receipt, receipt.caseId)
  if (r.metadata.category !== 'Document') throw Error('本片仅支持人工分类为 Document 的公开报告。')
  if (declaredPublic !== true) throw Error('请先确认报告及下列交接字段均可用于公开资料处理。')
  const source = publicSource(sourceUrl)
  return {
    profile: 'mcis-public-report-text-handoff-v1',
    original: { caseId: r.caseId, evidenceId: r.evidenceId, requestDigest: r.requestDigest,
      sourceSha256: r.sourceSha256, fileName: r.fileName, byteLength: r.byteLength,
      title: r.metadata.title, sourceDeclaration: r.metadata.source, registeredUtc: r.registeredUtc },
    publicMaterial: { sourceUrl: source, basis: 'user-declaration-only', verified: false },
    extraction: { scope: 'this-intake-entry-only', status: 'not-run', text: null, modelCalled: false },
    review: { status: 'unverified', factsConfirmed: false, authorAuthenticated: false },
    preservation: { storageClassification: 'Restricted', originalIncluded: false, originalModified: false },
  } as const
}

// Local JSON only. No fetch, original download, storage mutation, or parser invocation.
export function downloadHandoff(json: string): void {
  const anchor = document.createElement('a')
  const url = URL.createObjectURL(new Blob([json], { type: 'application/json;charset=utf-8' }))
  try {
    anchor.href = url
    anchor.download = 'public-report-text-handoff.json'
    document.body.append(anchor)
    anchor.click()
  } finally {
    anchor.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
}

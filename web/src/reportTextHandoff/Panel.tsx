import { useState } from 'react'
import type { Receipt } from '../evidenceIntake/model'
import { downloadHandoff, textHandoff } from './model'

export function ReportTextHandoff({ receipt }: { receipt: Receipt }) {
  // New receipt/case/version must never inherit a public-material declaration.
  return <Handoff key={JSON.stringify([receipt.caseId, receipt.evidenceId, receipt.requestDigest, receipt.sourceSha256, receipt.fileName, receipt.byteLength, receipt.registeredUtc, receipt.metadata])} receipt={receipt}/>
}
function Handoff({ receipt }: { receipt: Receipt }) {
  const [open, setOpen] = useState(false)
  const [source, setSource] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [message, setMessage] = useState('')
  if (receipt.metadata.category !== 'Document') return null
  const reset = () => { setOpen(false); setSource(''); setConfirmed(false); setMessage('') }
  const exportJson = () => {
    try {
      const manifest = textHandoff(receipt, source, confirmed)
      downloadHandoff(JSON.stringify(manifest, null, 2) + '\n')
      setMessage('已请求浏览器下载交接 JSON，请自行核对文件是否保存。原件不包含在内，未执行文本提取。')
    } catch (error) {
      setMessage('交接导出未完成；登记回执和当前输入仍保留，不会重新上传或自动重试。' + (error instanceof Error ? error.message : '请检查本地下载设置。'))
    }
  }
  return <section aria-label="公开报告文本提取交接">
    <h4>文本提取状态：本入口未解析</h4>
    <p>文件登记成功仅表示收到原字节；本入口未运行文本提取或 OCR，未产生可检索正文。证据哈希状态不能证明已解析，也不代表调查事实确认。其他工具是否解析过，本页未知。</p>
    {!open ? <button type="button" onClick={() => setOpen(true)}>准备公开报告待解析交接（本地）</button> : <div>
      <p>仅用于公开事故报告。导出含案件/证据编号、文件名、字节数、标题、原来源声明、登记 UTC、原件 SHA-256、请求摘要与下列地址；不含原件正文、提取人/登记人字段或登记备注。标题和原来源仍可能包含人员信息，请核查上述字段可用于公开资料处理，否则取消。不会改变 Restricted 存储标记。</p>
      <label>公开报告来源 HTTPS 地址（不访问）<input type="url" maxLength={2000} value={source} onChange={e => { setSource(e.target.value); setConfirmed(false); setMessage('') }}/></label>
      <label><input type="checkbox" checked={confirmed} onChange={e => { setConfirmed(e.target.checked); setMessage('') }}/>我声明这是公开事故报告，且所列交接字段可用于公开资料处理。此勾选不认证公开性、作者或事实。</label>
      <button type="button" disabled={!confirmed || !source} onClick={exportJson}>导出未解析交接 JSON</button>
      <button type="button" onClick={reset}>取消并清空交接输入</button>
      <p>仅显式本地导出；不会上传地址或调用解析服务。取消不删除已登记原件。重复导出相同内容不新增登记。</p>
      {message && <p role="status">{message}</p>}
    </div>}
  </section>
}

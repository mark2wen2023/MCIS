import { useEffect, useRef, useState } from 'react'
import { onIdentityChange } from '../api'
import { caseIdentity } from '../cases/identity'
import { exportPackage, packageError, verifyPackage } from './api'
import { packageFileError, packageFilename, type PackageCheck } from './model'
import '../styles/w8-package.css'
import { onPackageNavigation } from './navigation'

function useOperation(who: string) {
  const current = useRef<AbortController | null>(null)
  const alive = useRef(true)
  const cancel = () => { current.current?.abort(); current.current = null }
  useEffect(() => {
    alive.current = true
    const unsubscribe = onIdentityChange(cancel)
    const stopNavigation = onPackageNavigation(cancel)
    return () => { alive.current = false; cancel(); unsubscribe(); stopNavigation() }
  }, [])
  return {
    begin: () => {
      if (current.current || !alive.current || caseIdentity() !== who) return null
      const controller = new AbortController()
      current.current = controller
      return controller
    },
    valid: (controller: AbortController) => alive.current && !controller.signal.aborted && current.current === controller && caseIdentity() === who,
    end: (controller: AbortController) => { if (current.current === controller) current.current = null },
    cancel,
  }
}

export function PackageResult({ result }: { result: PackageCheck }) {
  return <div className={'w83-result ' + (result.isValid ? 'w83-pass' : 'w83-fail')} role="status">
    <h3>{result.isValid ? '清单哈希检查通过' : '清单哈希检查未通过'}</h3>
    <p>仅检查清单所列文件的缺失与 SHA-256 一致性，不代表来源真实、内容可信、审计链有效或可成功导入。</p>
    <dl><dt>清单案件编号</dt><dd>{result.caseId || '未提供'}</dd><dt>包格式</dt><dd>{result.packageFormat || '未提供'}</dd><dt>生成器</dt><dd>{result.generatorVersion || '未提供'}</dd><dt>生成时间</dt><dd>{result.createdAtUtc || '未提供'}</dd></dl>
    {([['missingFiles','缺失文件'],['tamperedFiles','哈希不符'],['extraFiles','清单外文件']] as const).map(([key,label])=><div key={key}><h4>{label} · {result[key].length}</h4>{result[key].length > 0 ? <ul className="w83-paths">{result[key].map((path,i)=><li key={i}><code>{path}</code></li>)}</ul> : <p>无</p>}</div>)}
    {result.extraFiles.length > 0 && <p className="w83-warning">清单外文件未被清单哈希覆盖。即使检查通过，也应单独核查这些文件。</p>}
    <p><strong>本次没有导入案件，也没有修改案件库。</strong></p>
  </div>
}

export function PackagePanel({ who }: { who: string }) {
  const [open, setOpen] = useState(false)
  useEffect(() => onPackageNavigation(() => setOpen(false)), [])
  return <section className="w83-package" aria-label="案件包工具">
    <div className="w83-heading"><div><span className="w83-eyebrow">.MCASE · 证据完整性</span><h2>案件包预检</h2></div><button type="button" aria-expanded={open} onClick={()=>setOpen(v=>!v)}>{open ? '关闭预检' : '选择案件包预检'}</button></div>
    <p>上传到本机调查服务核对清单。预检不等于导入。受限基础资料首次导入请使用独立的导入面板；完整案件包还原未开放。当前支持范围的案件包导出位于下方对应案件卡片；不是完整案件备份。匹配版本的受限归档仅在工作记录与依赖全部校验通过时支持同案号新案恢复（无W10时1.2.0工作记录扩展；含W10时须1.3.0）；未知或不支持内容整包拒绝，不会成功遗漏。HFACS当前版本最多支持256个完整修订及对应回执，超限整体拒绝，不截断历史。</p>
    {open && <PackageCheckForm key={who} who={who}/>}
  </section>
}
function PackageCheckForm({who}: {who: string}) {
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<PackageCheck | null>(null)
  const operation = useOperation(who)
  async function check() {
    if (!file) return
    const controller = operation.begin()
    if (!controller) return
    setBusy(true); setError(null); setResult(null)
    try { const report = await verifyPackage(file, who, controller.signal); if (operation.valid(controller)) setResult(report) }
    catch (err) { if (operation.valid(controller)) setError(packageError(err)) }
    finally { if (operation.valid(controller)) setBusy(false); operation.end(controller) }
  }
  return <div className="w83-form">
    <p className="w83-warning">只选择可信来源文件。100 MiB 是界面上传限制，不是服务端解压资源保护。选择文件不会立即上传，点击“上传并预检”才发送到本机服务。</p>
    <label>选择 .mcase 文件<input type="file" accept=".mcase" onChange={event=>{
      operation.cancel(); setBusy(false); setResult(null)
      const next = event.target.files?.[0] ?? null
      const issue = next ? packageFileError(next) : null
      setError(issue); setFile(issue ? null : next)
    }}/></label>
    {file && <p className="w83-selected">{file.name} · {(file.size/1024).toFixed(1)} KiB</p>}
    <div className="w83-actions"><button type="button" disabled={!file || busy} onClick={()=>void check()}>{busy ? '正在预检…' : '上传并预检'}</button>{busy && <button type="button" onClick={()=>{operation.cancel();setBusy(false);setError('已停止等待，服务端可能仍在检查；不会导入案件。')}}>停止等待</button>}</div>
    {error && <p role="alert" className="w83-warning">{error}</p>}
    {result && <PackageResult result={result}/>}
  </div>
}
export function PackageExport({caseId, title, who}: {caseId: string; title: string; who: string}) {
  const operation = useOperation(who)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  useEffect(() => onPackageNavigation(() => {setBusy(false); setMessage('')}), [])
  const urls = useRef(new Set<string>())
  useEffect(()=>()=>{for(const url of urls.current) URL.revokeObjectURL(url);urls.current.clear()},[])
  async function download() {
    const controller = operation.begin()
    if (!controller) return
    setBusy(true); setMessage('')
    try {
      const blob = await exportPackage(caseId, who, controller.signal)
      if (!operation.valid(controller)) return
      const url = URL.createObjectURL(blob); urls.current.add(url)
      const anchor = document.createElement('a'); anchor.href = url; anchor.download = packageFilename(caseId)
      document.body.appendChild(anchor); anchor.click(); anchor.remove()
      window.setTimeout(()=>{URL.revokeObjectURL(url);urls.current.delete(url)}, 1000)
      setMessage('已交给浏览器下载，请检查下载列表。仅包含当前支持范围的案件资料，不是全系统备份。导出或校验成功不等于笔录、报告可以完整恢复，原始资料须独立保管。')
    } catch(err) { if (operation.valid(controller)) setMessage(packageError(err)) }
    finally { if (operation.valid(controller)) setBusy(false); operation.end(controller) }
  }
  return <div className="w83-export"><p>完整性校验成功不等于可恢复。本功能不是完整案件备份；匹配版本的受限归档仅恢复列明的工作记录与历史（无W10时1.2.0工作记录扩展；含W10时须1.3.0），限同案号新案件、默认策略。未知模块、缺失依赖、预算超限整包拒绝；历史回执不可重放，过往确认不是本次审核。原始资料须独立保管。</p><button type="button" disabled={busy} onClick={()=>void download()} aria-label={'导出案件包：' + title}>{busy ? '正在准备案件包…' : '导出 .mcase'}</button>{message && <p role="status">{message}</p>}</div>
}

import React from 'react'
import fixed from '../single_seat_preview/result.json'

// Exact fixed-fixture admission, not a second general-purpose seat parser.
function same(a: unknown, b: unknown): boolean {
  if (a === b) return true
  if (!a || !b || typeof a !== 'object' || typeof b !== 'object') return false
  if (Array.isArray(a) !== Array.isArray(b)) return false
  if (!Array.isArray(a) && Object.getPrototypeOf(a) !== Object.prototype) return false
  const ak = Object.keys(a), bk = Object.keys(b)
  return ak.length === bk.length && bk.every(k => Object.hasOwn(a, k) && same((a as Record<string,unknown>)[k], (b as Record<string,unknown>)[k]))
}
export interface SingleSeatCardProps { preview: unknown }
export function SingleSeatCard({preview}: SingleSeatCardProps) {
  let accepted = false
  try { accepted = same(preview, fixed.preview) } catch { /* malformed/cyclic input fails closed */ }
  if (!accepted) return <section data-testid="single-seat-readonly-card" role="alert"><h2>单席意见不可展示</h2><p>输入与固定合成预览不一致。未确认、未保存；请核对来源与版本。</p></section>
  // Display the admitted frozen fixture, never unvalidated arbitrary fields.
  const p = fixed.preview
  return <section data-testid="single-seat-readonly-card" aria-label="海青君单席合成意见只读预览">
    <h2>海青君单席意见 · 只读合成预览</h2>
    <p>仅 T+124.250 开发控制；不是实际案件审核。</p>
    <dl><dt>案件</dt><dd>{p.caseId}</dd><dt>固定时刻（UTC）</dt><dd>{p.alignedUtc}</dd>
      <dt>人工处理状态</dt><dd role="status">待人工审核 · 未确认 · 未保存</dd></dl>
    <p>证据不足以判断任一船舶是否转向。缺少观测不等于没有转向。</p>
    <details><summary>固定意见原文</summary><p>{p.finding}</p></details>
    {p.rows.map((row,index) => <article key={row.itemId} aria-label={index===0?'A 船证据限制':'B 船证据限制'}>
      <h3>{index===0?'A 船':'B 船'} · {row.vesselId}</h3>
      <dl><dt>证据状态</dt><dd>{index===0?'已声明轨迹缺口':'该时刻无精确观测'}</dd>
        <dt>判断充分性</dt><dd>证据不足</dd><dt>出处定位</dt><dd>{row.reference
          ? <><code>{row.reference.evidenceId} {row.reference.jsonPointer}</code><p>合成宿主绑定的缺口定位；不是观测点。不可点击，未经真实授权读取或真实性核验。</p></>
          : '无精确观测引用；不借用 A 船缺口或邻近点。'}</dd></dl>
      <details><summary>该项原始说明与限制</summary><p>{row.statement}</p><p>{row.limitation}</p></details>
    </article>)}
    <p>此卡不提供确认、保存或原件访问操作，不进入笔录审核队列。</p>
  </section>
}

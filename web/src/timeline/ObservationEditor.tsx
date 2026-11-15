import {useEffect,useState,useSyncExternalStore} from 'react'
import {api,onIdentityChange} from '../api'
import type {EditableConflict} from './conflictEditing'
import {ObservationEditing} from './observationEditing'
export function ObservationEditor({caseId,conflict,onSaved}:{caseId:string;conflict:EditableConflict;onSaved:()=>void}){
  const [editor]=useState(()=>new ObservationEditing(caseId,conflict,api,onSaved))
  const s=useSyncExternalStore(editor.subscribe,editor.snapshot,editor.snapshot)
  useEffect(()=>onIdentityChange(editor.identityChanged),[editor])
  return <section aria-label={`${conflict.conflictId} 观察修改`} onClick={e=>e.stopPropagation()}>
    <button type="button" disabled={s.busy} onClick={editor.check}>检查来源权限以修改观察</button>
    <p>仅修改观察文字，来源标识不变。登记回执不证明用户已读、原件真实性或事实批准。草稿仅保留在本页，离开或重载会丢失。</p>
    {s.error&&<div role="alert">{s.error}</div>}{s.message&&<div role="status">{s.message}</div>}
    {s.allowed&&<div>
      {(['a','b'] as const).map(side=><div key={side}>
        <p>当前{side.toUpperCase()}：{s.current[side].sourceLabel} / {s.current[side].evidenceId??'来源未知'} / {s.current[side].valueText}</p>
        <label>拟修改{side.toUpperCase()}（{s.draft[side].evidenceId??'来源未知'}）<textarea value={s.draft[side].valueText} disabled={s.busy} onChange={e=>editor.edit(side,e.target.value)}/></label>
      </div>)}
      <button type="button" disabled={s.busy} onClick={editor.refresh}>重新读取当前记录并采用其编辑版本（保留草稿）</button>
      <button type="button" disabled={s.busy} onClick={editor.issue}>已比对拟修改内容，取得登记版本回执</button>
      {s.receipt&&<div><p>仅登记版本；到期：{s.receipt.expiresUtc}</p>
        {Object.entries(s.receipt.sources).map(([id,v])=><p key={id}>{id}：<code>{v.sha256}</code>；保管链位置：{v.custodyHeadSeq??'无'}</p>)}
        <button type="button" disabled={s.busy} onClick={editor.submit}>核对上述登记版本后提交观察</button>
      </div>}
    </div>}
  </section>
}

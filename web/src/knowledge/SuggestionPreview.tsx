import {useEffect,useRef,useState} from 'react'
import {request,identity} from './api'
import {ApiError} from '../api'
import type {Content} from './model'
import {parseSuggestion,type Suggestion,type SuggestionInput} from './suggestionModel'
import {SuggestionSourceReview} from './SuggestionSourceReview'
import {reviewedSuggestion} from './sourceReview'
import {previewSessionKey} from './previewSession'
type Props={input:SuggestionInput;onApply:(c:Content)=>void}
export function SuggestionPreview({input,onApply}:Props){
 // A changed source creates a fresh session: cleanup aborts and rejects late replies.
 return <SuggestionPreviewSession key={previewSessionKey(input,identity())} input={input} onApply={onApply}/>
}
function SuggestionPreviewSession({input,onApply}:Props){
 const [who]=useState(identity),[result,setResult]=useState<Suggestion|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false)
 const [acknowledgedDigest,setAcknowledgedDigest]=useState<string|null>(null)
 const active=useRef(true),pending=useRef(false),controller=useRef<AbortController|null>(null),generation=useRef(0)
 useEffect(()=>{active.current=true;return()=>{active.current=false;generation.current++;controller.current?.abort()}},[])
 function stopWaiting(){if(!active.current||!pending.current)return;generation.current++;controller.current?.abort();controller.current=null;pending.current=false;setBusy(false);setResult(null);setAcknowledgedDigest(null);setError('');}
 async function preview(){
  if(pending.current||!active.current||identity()!==who)return;
  const run=++generation.current;
  const current=()=>active.current&&generation.current===run&&identity()===who;
  pending.current=true;setBusy(true);setResult(null);setAcknowledgedDigest(null);setError('');controller.current=new AbortController();
  try{const value=parseSuggestion(await request('/suggestions',who,input,controller.current.signal),input);if(current())setResult(value)}
  catch(e){if(current())setError('预览读取失败，原候选未更改，可重试。'+(e instanceof ApiError?e.code+'：'+e.message:'连接或预览响应异常。'))}
  finally{if(active.current&&generation.current===run){pending.current=false;controller.current=null;setBusy(false)}}
 }
 return <section aria-label="来源模板整理预览"><h3>来源摘录 → 候选表单</h3><p>先填写下面的来源字段。仅复制与截取，不是模型推理或自动知识理解；不访问链接，不读取案件，不保存或公开。</p><button type="button" disabled={busy} onClick={()=>void preview()}>生成模板预览（不保存）</button>{busy&&<><p role="status">正在生成模板预览…</p><button type="button" onClick={stopWaiting}>停止等待（丢弃本次结果）</button><p>停止等待不代表服务器已停止处理；迟到结果不会填入草稿。</p></>}{error&&<p role="alert">{error}</p>}{result&&<div className="w19-warning"><p>template-stub-v1 · 非模型 · 未保存 · 待人工核查</p>{result.warnings.map(w=><p key={w}>{w}</p>)}<h4>{result.content.title}</h4><p>{result.content.summary}</p><details><summary>完整来源摘录与候选正文</summary><p className="w19-text">{result.content.body}</p><p>{result.content.source.title} · {result.content.source.locator}</p><p>使用权声明：{result.content.source.rightsNote}</p></details><p>输入SHA-256：<code>{result.inputDigest}</code>（仅版本标识，不证明真实性）</p><p>下方按钮会替换当前草稿标题、摘要、正文、标签及适用限制；不会保存。请检查后再手动保存为待审候选。</p><SuggestionSourceReview source={result.content.source} checked={acknowledgedDigest===result.inputDigest} onChange={v=>setAcknowledgedDigest(v?result.inputDigest:null)}/><button type="button" disabled={!reviewedSuggestion(result,input,acknowledgedDigest)} onClick={()=>{const content=reviewedSuggestion(result,input,acknowledgedDigest);if(content&&active.current&&identity()===who){onApply(content);setResult(null);setAcknowledgedDigest(null)}}}>核查后填入候选表单（不保存）</button></div>}</section>
}


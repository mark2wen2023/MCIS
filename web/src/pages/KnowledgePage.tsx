import {useCallback,useEffect,useRef,useState,useSyncExternalStore} from 'react'
import {getRole} from '../api'
import * as api from '../knowledge/api'
import {KINDS,STATUSES,permissions,utc,sample,type Card,type Content,type Status,type Kind,type Page} from '../knowledge/model'
import '../styles/w19.css'
import {KnowledgeArchivePanel} from '../knowledgeArchive/Panel'
import {SuggestionPreview} from '../knowledge/SuggestionPreview'
export function KnowledgePage(){const key=useSyncExternalStore(api.subscribe,api.context,api.context);return <KnowledgeWorkspace key={key}/>}
function KnowledgeWorkspace(){
 const [who]=useState(api.identity),[scope]=useState(api.context),access=permissions(getRole())
 const alive=useRef(true);useEffect(()=>{alive.current=true;return()=>{alive.current=false}},[])
 const valid=useCallback(()=>alive.current&&api.context()===scope,[scope])
 const lock=useSyncExternalStore(api.listenLock,api.lockState,api.lockState)
 const [filter,setFilter]=useState({status:'Published' as Status,kind:'',tag:'',q:'',offset:0})
 const [q,setQ]=useState(''),[tag,setTag]=useState(''),[kind,setKind]=useState('')
 const [result,setResult]=useState<Page|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState(''),[actionError,setActionError]=useState(''),[notice,setNotice]=useState(''),[tick,setTick]=useState(0),[ack,setAck]=useState(false)
 const previous=useRef(lock)
 useEffect(()=>{if(previous.current!==lock&&lock!=='pending')queueMicrotask(()=>{if(valid())setTick(n=>n+1)});previous.current=lock},[lock,valid])
 useEffect(()=>{const controller=new AbortController();let cancelled=false
  void Promise.resolve().then(async()=>{if(!valid()||cancelled)return;setLoading(true);setError('');setResult(null);setAck(false)
   try{const params=new URLSearchParams({status:filter.status,limit:'20',offset:String(filter.offset)});for(const k of ['kind','tag','q'] as const)if(filter[k])params.set(k,filter[k]);const d=await api.search(params,filter.status,who,controller.signal);if(valid()&&!cancelled)setResult(d)}catch(e){if(valid()&&!cancelled)setError(api.errorText(e))}finally{if(valid()&&!cancelled)setLoading(false)}})
  return()=>{cancelled=true;controller.abort()}
 },[filter,who,tick,valid])
 async function run(action:()=>Promise<Card>,created=false){if(!valid()||!access.internal||!api.begin())return;setNotice('');setActionError('');let outcome:'idle'|'unknown'='idle'
  try{const d=await action();if(valid()){setNotice(`${d.cardId} · ${STATUSES[d.status]}。以服务返回状态为准，发布不等于事实认证。`);if(created)setFilter({status:'Candidate',kind:'',q:'',tag:'',offset:0})}}
  catch(e){if(api.uncertain(e))outcome='unknown';if(valid())setActionError(api.errorText(e))}finally{api.setLock(outcome)}
 }
 return <main className="w19" aria-labelledby="knowledge-heading"><header><span>W19 · 人工维护的知识资料库</span><h1 id="knowledge-heading">案例、疑难与方法知识卡</h1><p>全局资料库，与当前案件无关。这里只收明确公开或合成内容，不读取真实案件、内网材料，也不调用模型或训练。</p></header>
 <p className="w19-warning">来源链接、摘录及使用权仍需人工核实。内容哈希只标识版本，不证明真实性或已获授权。检索为字面与标签匹配，不是语义相似度或调查结论。</p>
 <KnowledgeArchivePanel/><form className="w19-search" onSubmit={e=>{e.preventDefault();setFilter({...filter,kind,q,tag,offset:0})}}><label>字面关键词<input value={q} maxLength={160} onChange={e=>setQ(e.target.value)}/></label><label>类型<select value={kind} onChange={e=>setKind(e.target.value)}><option value="">全部类型</option>{Object.entries(KINDS).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><label>精确标签<input maxLength={40} value={tag} onChange={e=>setTag(e.target.value)}/></label><button type="submit" disabled={loading}>检索</button></form>
 {access.internal&&<label className="w19-status">资料状态<select value={filter.status} disabled={lock==='pending'} onChange={e=>setFilter({...filter,status:e.target.value as Status,offset:0})}>{Object.entries(STATUSES).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>}
 <div className="w19-actions"><button disabled={loading||lock==='pending'} onClick={()=>setTick(n=>n+1)}>重新读取</button><span>{access.internal?'内部候选不向外部角色展示；只有首席可批准发布。':'只读已发布公开/合成知识卡；未审批或撤回内容不可访问。'}</span></div>
 {lock==='pending'&&<p role="status">写入进行中。离开页面不会撤销服务处理，请勿重复操作。</p>}{notice&&<p role="status">{notice}</p>}{error&&<p role="alert" className="w19-warning">{error}</p>}{actionError&&<p role="alert" className="w19-warning">{actionError}</p>}
 {lock==='unknown'&&access.internal&&<div className="w19-warning"><p>结果未确认，禁止自动重发。重新读取相应队列并核查审计后才解除锁定；整页刷新不代表原请求撤销。</p><label><input type="checkbox" checked={ack} disabled={loading||!!error} onChange={e=>setAck(e.target.checked)}/>我已核查服务器队列和审计，确认不会重复写入</label><button disabled={!ack||loading||!!error} onClick={()=>{api.setLock('idle');setAck(false);setActionError('')}}>核查后解除锁定</button></div>}
 {access.internal&&<AuditReader who={who} valid={valid}/>}
 {access.internal&&<CreateCard disabled={lock!=='idle'} onCreate={c=>void run(()=>api.create(c,who),true)}/>}
 {loading?<p role="status">读取知识卡…</p>:result&&<><h2>{STATUSES[filter.status]} <small>{result.total} 条</small></h2>{result.items.length===0?<p className="w19-empty">没有符合条件的知识卡。库为空时不伪造样本或模型推荐。</p>:result.items.map(c=><KnowledgeCard key={c.cardId+c.status+tick} card={c} canReview={access.review&&lock==='idle'} onReview={(decision,note,approved)=>void run(()=>api.review(c.cardId,decision,c.contentDigest,note,approved,who))}/>)}<div className="w19-actions"><button disabled={!filter.offset} onClick={()=>setFilter({...filter,offset:Math.max(0,filter.offset-20)})}>上一页</button><span>第 {Math.floor(filter.offset/20)+1} 页</span><button disabled={filter.offset+result.items.length>=result.total||filter.offset>=10000} onClick={()=>setFilter({...filter,offset:filter.offset+20})}>下一页</button></div></>}
 <p>本片不提供向量相似度、RAG、自动案例采集、事故分级或通知义务判定。现有角色头仅适用于本机演示，不是生产认证。</p></main>
}
export function KnowledgeCard({card,canReview,onReview}:{card:Card;canReview:boolean;onReview:(s:Status,n:string,a:boolean)=>void}){
 const [note,setNote]=useState(''),[checks,setChecks]=useState<boolean[]>([false,false,false]);const c=card.content,source=c.source
 return <article className="w19-card"><div className="w19-card-top"><span>{KINDS[c.kind]} · {source.type==='Synthetic'?'合成样本，非真实事故':'公开来源（人工声明）'}</span><strong>{STATUSES[card.status]}</strong></div><h3>{c.title}</h3><p>{c.summary}</p><div className="w19-tags">{c.tags.map(t=><span key={t}>{t}</span>)}</div><details><summary>正文、出处与适用限制</summary><p className="w19-text">{c.body}</p><h4>适用范围与限制</h4><p>{c.applicability}</p><h4>原始来源</h4><p>{source.title} · {source.locator}</p>{source.url&&<a href={source.url} target="_blank" rel="noopener noreferrer">打开人工登记的公开来源（未自动核验）</a>}<blockquote>{source.excerpt}</blockquote><p>使用权说明：{source.rightsNote}</p><p>来源链接和摘录需人工确认，系统没有抓取或比对原文。</p><p><code>{card.cardId}</code> · 创建 {utc(card.createdUtc)}</p><p>内容 SHA-256：<code>{card.contentDigest}</code></p>{card.reviewedUtc&&<p>最近审核 {utc(card.reviewedUtc)} · {card.reviewedBy||'人工审核'} {card.reviewNote||''}</p>}</details>
 {canReview&&(card.status==='Candidate'||card.status==='Published')&&<form className="w19-review" onSubmit={e=>e.preventDefault()}><label>审核理由<textarea required maxLength={2000} value={note} onChange={e=>setNote(e.target.value)}/></label>{card.status==='Candidate'?<>{['我已核对来源、定位和摘录，内容与来源一致（合成样本已明确标注）','我已核实使用权与披露范围，不含未获授权的个人或内网信息','我明确批准把这份内容向全部知识库角色公开'].map((s,i)=><label key={s} className="w19-check"><input type="checkbox" checked={checks[i]} onChange={e=>setChecks(a=>a.map((v,j)=>i===j?e.target.checked:v))}/>{s}</label>)}<div className="w19-actions"><button disabled={!note.trim()} onClick={()=>onReview('Rejected',note.trim(),false)}>驳回，不公开</button><button disabled={!note.trim()||!checks.every(Boolean)} onClick={()=>onReview('Published',note.trim(),true)}>批准发布到公开资料库</button></div></>:<button disabled={!note.trim()} onClick={()=>onReview('Withdrawn',note.trim(),false)}>撤回并移出公开检索</button>}</form>}
 </article>
}
function CreateCard({disabled,onCreate}:{disabled:boolean;onCreate:(c:Content)=>void}){
 const empty:Content={kind:'Case',title:'',summary:'',body:'',tags:[],applicability:'',source:{type:'Synthetic',title:'',locator:'',excerpt:'',rightsNote:''}}
 const [form,setForm]=useState<Content>(empty),[tags,setTags]=useState('')
 const set=(k:'title'|'summary'|'body'|'applicability',v:string)=>setForm({...form,[k]:v})
 const source=(k:'title'|'locator'|'excerpt'|'rightsNote'|'url',v:string)=>setForm({...form,source:{...form.source,[k]:v}})
 return <details className="w19-create"><summary>人工创建候选（不会自动公开）</summary><form onSubmit={e=>{e.preventDefault();onCreate({...form,tags:tags.split(',').map(t=>t.trim()).filter(Boolean)})}}><fieldset disabled={disabled}><legend>仅录入公开或合成材料，禁止真实内网或私人资料</legend><button type="button" onClick={()=>{setForm(structuredClone(sample));setTags(sample.tags.join(','))}}>在表单中填入合成示例（不保存）</button><label>卡片类型<select value={form.kind} onChange={e=>setForm({...form,kind:e.target.value as Kind})}>{Object.entries(KINDS).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
 {(['title','summary','body','applicability'] as const).map((k,i)=><label key={k}>{['标题','摘要','正文','适用范围与限制'][i]}<textarea required maxLength={[160,600,6000,1000][i]} value={form[k]} onChange={e=>set(k,e.target.value)}/></label>)}
 <label>标签（英文逗号分隔，最多8个）<input required value={tags} maxLength={327} onChange={e=>setTags(e.target.value)}/></label><label>来源类型<select value={form.source.type} onChange={e=>{const s={...form.source,type:e.target.value as 'Public'|'Synthetic'};delete s.url;setForm({...form,source:s})}}><option value="Synthetic">合成样本</option><option value="Public">公开资料（仍需明确审批）</option></select></label>
 {(['title','locator','excerpt','rightsNote'] as const).map((k,i)=><label key={k}>{['来源标题','页码/章节/段落定位','原文摘录','使用权与公开依据说明'][i]}<textarea required maxLength={[240,240,2000,1000][i]} value={form.source[k]} onChange={e=>source(k,e.target.value)}/></label>)}
 {form.source.type==='Public'&&<label>HTTPS来源链接<input required type="url" maxLength={1000} value={form.source.url||''} onChange={e=>source('url',e.target.value)}/></label>}
 <SuggestionPreview key={JSON.stringify([form.kind,form.source])} input={{kind:form.kind,source:form.source}} onApply={c=>{setForm(c);setTags(c.tags.join(','))}}/><button type="submit">保存为内部待审候选</button></fieldset></form></details>
}

function AuditReader({who,valid}:{who:string;valid:()=>boolean}){
 const [lines,setLines]=useState<string[]>([]),[message,setMessage]=useState(''),[busy,setBusy]=useState(false)
 async function read(){if(busy||!valid())return;setBusy(true);setLines([]);setMessage('')
  try{const data=await api.request('/audit?order=desc&limit=50',who);if(!Array.isArray(data)||!data.every(x=>x&&typeof x.seq==='number'&&typeof x.cardId==='string'&&typeof x.action==='string'&&typeof x.utc==='string'&&typeof x.operator==='string'))throw Error('审计格式异常');if(valid()){setLines(data.map(x=>`${x.seq} · ${x.utc} · ${x.cardId} · ${x.action} · ${x.operator}`));setMessage('已读取最近50条审计；这是操作记录，不证明来源真实性。')}}catch(e){if(valid())setMessage(api.errorText(e))}finally{if(valid())setBusy(false)}}
 return <details className="w19-audit"><summary>内部审计核查</summary><button disabled={busy} onClick={()=>void read()}>读取最近50条审计</button><p role="status">{message}</p><ol>{lines.map(line=><li key={line}>{line}</li>)}</ol></details>
}

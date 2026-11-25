import {useLayoutEffect,useMemo,useRef,useState} from 'react';
import {immutableEvents,JournalWriteConflict,SourceSelectionChanged,parseSources,parseIssueList,type IssueSummary,type SourceCandidate,canDiscuss,createRehearsalPort,latest,parse,type Command,type History,type JournalPort,type Kind} from './model';
/** Unmounted trial component. Default disconnected; no credentials, old API or storage. */
export function IssueWorkspace({caseId='CASE-ISSUE-FICTIONAL',port,rehearsal=false,contextKey='',issueId}:{caseId?:string,port?:JournalPort,rehearsal?:boolean,contextKey?:string,issueId?:string}){
 const demo=useMemo(()=>rehearsal&&!port&&caseId==='CASE-ISSUE-FICTIONAL'?createRehearsalPort():undefined,[caseId,port,rehearsal,contextKey]);
 const connection=(port&&contextKey.trim()&&contextKey.length<=128?port:undefined)??demo;const validCase=/^[A-Za-z0-9_-]{1,64}$/.test(caseId)&&(!issueId||/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(issueId));
 const [cards,setCards]=useState<IssueSummary[]>([]),[listStatus,setListStatus]=useState('尚未读取问题卡目录');
 const [sources,setSources]=useState<SourceCandidate[]>([]),[selected,setSelected]=useState<string[]>([]),[sourceStatus,setSourceStatus]=useState('尚未读取来源');
 const [history,setHistory]=useState<History>();const [note,setNote]=useState('');const [kind,setKind]=useState<Kind>('judgment');
 const [outcome,setOutcome]=useState<'supports'|'refutes'|'inconclusive'>('inconclusive');
 const [draftTarget,setDraftTarget]=useState<number|null>(null);
 const [targetChanged,setTargetChanged]=useState<{old:number|null,current:number}>();
 const [draftRecovery,setDraftRecovery]=useState(false);
 const [reselectBeforeSave,setReselectBeforeSave]=useState(false);
 const [readBlocked,setReadBlocked]=useState(false);const issueRef=useRef<string|undefined>(undefined);
 const [busy,setBusy]=useState(false);const [unknown,setUnknown]=useState(false);const [status,setStatus]=useState('未连接安全试验接口');
 const knownCards=useRef(new Map<string,History>());
 const baseline=useRef<History|undefined>(undefined);
 const epoch=useRef(0),locked=useRef(false),pending=useRef<Command|undefined>(undefined);
 useLayoutEffect(()=>{epoch.current++;knownCards.current.clear();setCards([]);setListStatus('尚未读取问题卡目录');setSources([]);setSelected([]);setSourceStatus('尚未读取来源');locked.current=false;pending.current=undefined;issueRef.current=issueId;baseline.current=undefined;setDraftTarget(null);setTargetChanged(undefined);setDraftRecovery(false);setReselectBeforeSave(false);setReadBlocked(!!issueId);setHistory(undefined);setNote('');setKind('judgment');setUnknown(false);setBusy(false);setStatus(demo?'虚构内存试用：刷新即丢失，未写入数据库':connection?'试验接口已提供，非生产登录':'未连接安全试验接口');return ()=>{epoch.current++;pending.current=undefined;baseline.current=undefined}},[caseId,connection,demo,contextKey,issueId]);
 async function save(retry=false){
  if(locked.current||!connection||!validCase)return;
  let command=pending.current;
  if(!retry){
   if(targetChanged||unknown||readBlocked||reselectBeforeSave&&!selected.length||!note.trim()||note.length>8000||kind!=='judgment'&&!history||kind==='discussion'&&!canDiscuss(history))return;
   if(kind!=='judgment'&&(draftTarget===null||draftTarget!==latest(history))){setTargetChanged({old:draftTarget,current:latest(history)});setReadBlocked(true);setDraftRecovery(true);return}
   command={caseId,issueId:history?.issueId??crypto.randomUUID(),operationId:crypto.randomUUID(),expectedRevision:history?.revision??0,
    ...(selected.length?{sourcePins:selected.map(id=>{const source=sources.find(s=>s.evidenceId===id)!;return {evidenceId:id,sourceIncarnation:source.sourceIncarnation,sourceSha256:source.sourceSha256}})}:{}),
    entry:{kind,note,sourceIds:[...selected],outcome:kind==='verification'?outcome:null,againstJudgment:kind==='judgment'?null:draftTarget}};pending.current=command;
  }
  if(!command)return;issueRef.current=command.issueId;const mine=epoch.current;locked.current=true;setBusy(true);setHistory(old=>old&&({...old,events:immutableEvents(old.events)}));setStatus('正在提交工作记录，不代表事实审核');
  try{const value=await connection.save(structuredClone(command));if(mine!==epoch.current)return;
   const next=parse(value,caseId,command.issueId);
   if(next.revision<command.expectedRevision+1||history&&JSON.stringify(immutableEvents(next.events.slice(0,history.revision)))!==JSON.stringify(immutableEvents(history.events)))throw Error('invalid history');
   const recorded=next.events[command.expectedRevision];
   if(JSON.stringify({kind:recorded.kind,note:recorded.note,sourceIds:recorded.sourceIds,outcome:recorded.outcome,againstJudgment:recorded.againstJudgment})!==JSON.stringify(command.entry))throw Error('mismatched receipt');
   baseline.current=next;knownCards.current.set(next.issueId,next);setHistory(next);pending.current=undefined;setUnknown(false);setSelected([]);setReselectBeforeSave(false);setNote('');setDraftTarget(null);setTargetChanged(undefined);setKind('judgment');setStatus(demo?'仅保存在本页内存；未写入数据库':'试验服务已返回工作记录，未审核');
  }catch(error){if(mine===epoch.current&&error instanceof SourceSelectionChanged){pending.current=undefined;setCards([]);setListStatus('操作未确认，请重新读取目录');setSources([]);setSelected([]);setUnknown(false);setSourceStatus('来源版本已变化：请重新读取并选择');setStatus('本次来源版本不匹配，未写入；保留意见，请重新选择来源后提交')}else if(mine===epoch.current&&error instanceof JournalWriteConflict){
   pending.current=undefined;setCards([]);setListStatus('本次追加被拒绝，请先授权重读历史');
   setHistory(undefined);setSources([]);setSelected([]);setUnknown(false);
   setReselectBeforeSave(command.entry.sourceIds.length>0);
   setSourceStatus('已清空提交时的来源选择');setReadBlocked(true);setDraftRecovery(true);
   setStatus('本次追加冲突，试验服务明确拒绝。保留未提交文字，请先重读历史。');
  }else if(mine===epoch.current){setCards([]);setListStatus('操作未确认，请重新读取目录');setSources([]);setSelected([]);setSourceStatus('操作未确认，已隐藏来源；原操作保留待重试');setUnknown(true);setStatus('结果未确认：保留原操作重试，勿改写后重复提交。')}}
  finally{if(mine===epoch.current){locked.current=false;setBusy(false)}}
 }
 async function refresh(recoverDraft=false){
  if(locked.current||targetChanged||!connection||!validCase||!issueRef.current||unknown||(note.length>0&&!(recoverDraft&&draftRecovery)))return;const mine=epoch.current;locked.current=true;setBusy(true);setHistory(undefined);
  try{const value=await connection.read(caseId,issueRef.current);if(mine!==epoch.current)return;const next=parse(value,caseId,issueRef.current);const known=baseline.current;if(known&&(next.revision<known.revision||JSON.stringify(immutableEvents(next.events.slice(0,known.revision)))!==JSON.stringify(immutableEvents(known.events))))throw Error('changed history');baseline.current=next;knownCards.current.set(next.issueId,next);setHistory(next);const changed=recoverDraft&&kind!=='judgment'&&(draftTarget===null||draftTarget!==latest(next));setTargetChanged(changed?{old:draftTarget,current:latest(next)}:undefined);setReadBlocked(changed);setDraftRecovery(changed);setStatus(changed?'草稿针对的判断已变化，禁止提交；请放弃后重新开始':recoverDraft?'已授权重读，草稿可继续编辑；请重新选择当前来源':'已重新读取未审核历史')}
  catch{if(mine===epoch.current){setCards([]);setListStatus('历史读取未确认，目录已隐藏');setSources([]);setSelected([]);setSourceStatus('历史读取未确认，已隐藏来源');setHistory(undefined);setReadBlocked(true);if(!recoverDraft){setNote('');setKind('judgment')}setStatus('读取未确认，已隐藏历史；不得据此认定记录已删除')}}
  finally{if(mine===epoch.current){locked.current=false;setBusy(false)}}
 }
 async function loadSources(){
  if(locked.current||!connection?.sources||!validCase||unknown)return;const mine=epoch.current;locked.current=true;setBusy(true);setHistory(old=>old&&({...old,events:immutableEvents(old.events)}));setSources([]);setSelected([]);setSourceStatus('正在核验当前来源');
  try{const value=await connection.sources(caseId);if(mine!==epoch.current)return;setSources(parseSources(value,caseId));setSourceStatus('已读取当前本地支持的来源；保存时服务端会再次核验，不代表事实已审核')}
  catch{if(mine===epoch.current){setCards([]);setListStatus('来源读取未确认，目录已隐藏');setSources([]);setSelected([]);setSourceStatus('来源读取未确认，已清空选择');setHistory(undefined);setReadBlocked(!!issueRef.current);setDraftRecovery(!!issueRef.current&&note.length>0)}}
  finally{if(mine===epoch.current){locked.current=false;setBusy(false)}}
 }
 async function loadCards(){
  if(locked.current||!connection?.list||!validCase||unknown||note.length)return;
  const mine=epoch.current;locked.current=true;setBusy(true);setHistory(old=>old&&({...old,events:immutableEvents(old.events)}));setCards([]);setListStatus('正在读取未审核问题卡目录');
  try{const value=await connection.list(caseId);if(mine!==epoch.current)return;setCards(parseIssueList(value,caseId));setListStatus('目录仅供选择，须重新读取卡片后才能追加；不是事实审核')}
  catch{if(mine===epoch.current){setCards([]);setListStatus('目录读取未确认，已隐藏内容');setHistory(undefined);setReadBlocked(!!issueRef.current);setSources([]);setSelected([])}}
  finally{if(mine===epoch.current){locked.current=false;setBusy(false)}}
 }
 function chooseCard(id?:string){
  if(locked.current||unknown||note.length||!connection||!validCase||id&&!cards.some(c=>c.issueId===id))return;
  epoch.current++;pending.current=undefined;issueRef.current=id;baseline.current=id?knownCards.current.get(id):undefined;
  setDraftTarget(null);setTargetChanged(undefined);setDraftRecovery(false);setReselectBeforeSave(false);setHistory(undefined);setReadBlocked(!!id);setSources([]);setSelected([]);setSourceStatus('尚未读取来源');setKind('judgment');setOutcome('inconclusive');setStatus(id?'已选择问题卡，请重新读取历史后追加':'新卡尚未创建，填写初判并提交才保存');
 }
 const disabled=!connection||!validCase||busy||unknown||readBlocked;
 return <section aria-label="问题研判工作区试验"><h2>问题研判记录 · 未审核</h2>
 <p>{demo?'虚构数据、纯内存演练，不是数据库保存。':'独立非生产组件；尚非完整工作台或生产登录。'}</p>
 <p>保留判断变化，不自动认定事实、责任或专家共识。核实结果也是调查员提交的工作意见。</p>
 <p role="status">{status}</p>{issueRef.current&&!history&&<p>指定问题卡须先重新读取；读取失败不代表可以另建或覆盖。</p>}<p>案件：{caseId}；版本：{history?.revision??0}</p>
 <fieldset disabled={!connection||!validCase||busy||unknown||note.length>0}><legend>未审核问题卡目录</legend>
 <button type="button" disabled={!connection?.list||busy||unknown||note.length>0} onClick={()=>void loadCards()}>刷新问题卡目录</button>
 <button type="button" onClick={()=>chooseCard()}>新建空卡（尚未保存）</button><p>{listStatus}</p>
 {cards.map(card=><div key={card.issueId}><button type="button" aria-label={'打开问题卡 '+card.issueId} onClick={()=>chooseCard(card.issueId)}>打开问题卡 {card.issueId}</button><span> · v{card.revision} · 未审核 · {card.openingNotePreview}</span></div>)}
 </fieldset>{note.length>0&&<p>有未提交意见，暂不能切换卡片或刷新目录；请先提交或手动清空意见。</p>}
 <label>记录类型 <select aria-label="记录类型" disabled={disabled} value={kind} onChange={e=>{const value=e.target.value as Kind;setKind(value);setDraftTarget(value==='judgment'?null:latest(history))}}>
 <option value="judgment">{history?'新的判断（保留旧判断）':'初步判断'}</option>
 <option value="verification" disabled={!history}>核实记录</option><option value="discussion" disabled={!canDiscuss(history)}>讨论记录（须先核实最新判断）</option></select></label>
 {kind==='verification'&&<label>核实结果 <select aria-label="核实结果" disabled={disabled} value={outcome} onChange={e=>setOutcome(e.target.value as typeof outcome)}><option value="inconclusive">未能确定</option><option value="supports">支持当前判断</option><option value="refutes">反驳当前判断</option></select></label>}
 <fieldset disabled={disabled}><legend>引用已登记来源（最多 20 项）</legend>
 <button type="button" disabled={disabled||!connection?.sources} onClick={()=>void loadSources()}>读取当前来源</button><p>{sourceStatus}</p>
 {sources.map(source=><label key={source.evidenceId}><input type="checkbox" aria-label={'引用 '+source.evidenceId} checked={selected.includes(source.evidenceId)} disabled={disabled||selected.length>=20&&!selected.includes(source.evidenceId)} onChange={e=>setSelected(old=>e.target.checked?(old.includes(source.evidenceId)||old.length>=20?old:[...old,source.evidenceId]):old.filter(id=>id!==source.evidenceId))}/>{source.evidenceId} · {source.mediaKind} · {source.byteLength} 字节 · SHA256 {source.sourceSha256}</label>)}
 <p>仅清单引用，不上传附件、不表示已阅读原件；清单缺项不表示案件没有其他证据。保存必须匹配所选来源代次与 SHA256；变化则拒绝写入，请重新读取并选择。</p></fieldset>
 {targetChanged&&<p role="alert">原草稿针对判断 #{targetChanged.old??'未知'}；当前判断 #{targetChanged.current}。不自动重绑，不可提交；仅可放弃后重读。</p>}
 {draftRecovery&&<aside aria-label="未提交草稿恢复"><p>未提交文字仍保留，但暂不可编辑或提交。原来源选择已清空，请先授权重读历史。</p>
 <button type="button" disabled={busy||!!targetChanged||!connection||!validCase} onClick={()=>void refresh(true)}>重读历史以恢复草稿</button>
 <button type="button" disabled={busy} onClick={()=>{setNote('');setKind('judgment');setDraftTarget(null);setTargetChanged(undefined);setDraftRecovery(false);setReselectBeforeSave(false);setReadBlocked(true);setStatus('已放弃未提交文字；仍须授权重读历史')}}>放弃未提交文字</button></aside>}
 <label>意见与理由 <textarea aria-label="意见与理由" maxLength={8000} disabled={disabled} value={note} onChange={e=>{if(!note&&e.target.value&&kind!=='judgment')setDraftTarget(latest(history));setNote(e.target.value)}}/></label>
 {reselectBeforeSave&&!selected.length&&<p>本草稿原先引用了来源，请重新读取并选择当前来源后提交。</p>}
 <button type="button" disabled={disabled||reselectBeforeSave&&!selected.length||!note.trim()} onClick={()=>void save()}>追加记录，不覆盖历史</button>
 {unknown&&<button type="button" disabled={busy||!connection} onClick={()=>void save(true)}>按原操作重试</button>}
 <button type="button" disabled={!connection||!validCase||!issueRef.current||busy||unknown||note.length>0} onClick={()=>void refresh()}>重新读取历史</button>
 <ol>{history?.events.map(e=><li key={e.seq}><strong>#{e.seq} · {{judgment:'判断',verification:'核实记录',discussion:'讨论记录'}[e.kind]}</strong><p>{e.note}</p><small>{e.recordedUtc}{e.againstJudgment?` · 针对判断 #${e.againstJudgment}`:''}{e.outcome?` · ${{supports:'支持',refutes:'反驳',inconclusive:'未能确定'}[e.outcome]}`:''}</small>{!!e.sourceIds.length&&<p>历史来源引用：{e.sourceIds.join('、')}；不是当前原件有效性证明。</p>}{e.sourceIds.map(id=><p key={id} data-source-version={id}>{id} · {({current:'当前（本次读取核对）',needs_review:'待复核',unavailable:'不可用'} as const)[e.sourceVersionStates?.find(x=>x.evidenceId===id)?.status as 'current'|'needs_review'|'unavailable']??'未核对（响应未提供状态）'}；不代表事实已确认。</p>)}</li>)}</ol>
 <p>本页暂不录入来源附件、不归档；切换案件或接口会隐藏旧内容，但不撤销服务端可能已提交的操作。</p></section>;
}

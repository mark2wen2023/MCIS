import {parseMeeting,compareRoles,type MeetingDisplay} from './meeting'
import {packet, PACKET_SHA, MAX_BYTES, ROLE_NAMES, parseResult, mode, comparison, type Result} from './model'
const phaseText:Record<string,string>={ready:'尚未开始',round_open:'本轮尚未完成',round_review:'首轮完成待审读；会议尚未完成',completed_unverified:'两轮完成；全部意见未核实',stopped_by_operator:'人工停止；不代表会议完成',stopped_failed:'失败停止；不代表会议完成',stopped_unknown:'结果未知；不代表会议完成',timed_out:'超时停止；不代表会议完成'}
const roleText:Record<string,string>={not_started:'尚未开始',unknown:'结果未知',not_accepted:'未接受',completed_unverified:'意见已接受但未核实'}
export function mount(root:HTMLElement, embedded?:MeetingDisplay) {
  let meeting=embedded?parseMeeting(new TextEncoder().encode(JSON.stringify(embedded))):null,roundIndex=0
  let result:Result|null=null, selected=packet.items[0].itemId, filter='all', generation=0
  const el=(tag:string,text?:string,className?:string)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n}
  const header=el('header');header.append(el('p','MCIS / PUBLIC RESEARCH','eyebrow'),el('h1','双视角审读工作台'),el('p','公开报告冻结片段 · 不是真人专家 · 全部意见未核实'))
  const notice=el('aside','仅在本地查看公开材料的结果 JSON。不接入案件、不运行模型、不上传。相同标签不是共识，分歧不自动裁决。三条人工编写测试主张（含反例）均对应同一份报告的同一页（PDF 第 28 页 / 印刷页 26），不是三份独立证据。','notice')
  const controls=el('section',undefined,'toolbar'),label=el('label','选入 a686c85 的 result.json（最大 1 MiB） '),file=document.createElement('input');file.type='file';file.accept='.json,application/json';label.append(file)
  const clear=el('button','清空结果') as HTMLButtonElement;clear.type='button';controls.append(label,clear)
  const status=el('p',meeting?'已载入只读会议视图；全部意见未核实，没有执行模型。':'尚未载入结果。只接受冻结 YANGZE 22 公开片段，不接受其他案例。');status.setAttribute('role','status');status.setAttribute('aria-live','polite')
  const provenance=el('section',undefined,'provenance'),body=el('div',undefined,'workspace'),nav=el('nav');nav.setAttribute('aria-label','主张选择')
  const detail=el('section');detail.setAttribute('aria-label','主张与双角色意见');body.append(nav,detail)
  root.replaceChildren(header,notice,controls,status,provenance,body)
  function draw(){
    provenance.replaceChildren();nav.replaceChildren();detail.replaceChildren()
    label.hidden=!!meeting;file.disabled=!!meeting
    if(!result&&!meeting){detail.append(el('h2','准备审读'),el('p','从已保存的公开案例运行目录选入 result.json。此页不包含预置模型答案，也不会自动执行模型。'));return}
    const r=result
    if(meeting){
      const m=meeting
      provenance.append(el('h2',m.transportMode==='remote_mock'?'MockHTTP 协议结果 · 非真实模型验收':m.realDeepSeekExecuted?'声明收到远端响应 · 模型身份与能力未认证':'远端模式声明 · 未声明收到响应 · 非成功调用证明'),el('p',`会议状态：${phaseText[m.meetingPhase]}（${m.meetingPhase}） · ${m.receiptComplete?'回执声明完整不代表会议完成':'回执未声明完整'} · 全部意见未核实`),el('p',`会议 ID：${m.meetingId}`,'mono'),el('p',`协议请求预留 ${m.budget.totalModels}/16 · 工具 ${m.budget.totalTools}/32 · 已返回 ${m.budget.received} · 未知 ${m.budget.unknown} · 未派发 ${m.budget.notDispatched}`),el('p',`原始复合回执 SHA-256：${m.receiptSha256}`,'mono'),el('p','受控流程须先用显式本地转换器校验原回执链；本页不能证明已执行该转换。浏览器只校验展示结构，不重放全部回执、不认证作者、模型或源PDF。计数、模式与摘要均为未认证声明。只读审查，不授权新模型调用。','warning'))
      if(!m.rounds.length){detail.append(el('p','尚无已开始轮次；不补造专家意见。'));return}
      const rounds=document.createElement('select');rounds.setAttribute('aria-label','选择审读轮次')
      m.rounds.forEach((rd,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=`第 ${rd.number} 轮`;rounds.append(o)})
      rounds.value=String(roundIndex);rounds.addEventListener('change',()=>{roundIndex=Number(rounds.value);filter='all';selected=packet.items[0].itemId;draw();(provenance.querySelector('select') as HTMLSelectElement)?.focus()});provenance.append(rounds,el('p',roundIndex===0?'本轮不读取其他角色意见。':'本轮两角色仅共享同一份完整上一轮意见；不是同轮实时互相阅读。'))
    }else if(r) provenance.append(el('h2',mode(r)),el('p',`运行状态：${r.status} / ${r.outcome} · 未核实`),el('p',`运行 ID：${r.runId}`,'mono'),el('p',`声明运行 Pi：${r.realPi} · 提供方请求次数：${r.providerRequests} · 模型：deepseek-v4-pro`),el('p',`来源包 SHA-256：${PACKET_SHA}`,'mono'),el('p','仅校验本地 JSON 结构与冻结来源绑定；未核验 completion.json 或回执链，不能证明导出完整、真实调用、作者或源PDF真实性。','warning'))
    const roles=meeting?meeting.rounds[roundIndex].roles:r!.roles
    const viewResult={roles}
    if(r?.errorCode) provenance.append(el('p',`未接受原因代码：${r.errorCode}`))
    const counts={same:0,different:0,missing:0};for(const item of packet.items) counts[compareRoles(viewResult,item.itemId).kind as keyof typeof counts]++
    const select=document.createElement('select');select.setAttribute('aria-label','筛选意见状态')
    for(const [value,text] of [['all','全部主张'],['different',`标签分歧 ${counts.different}`],['same',`标签相同 ${counts.same}（非共识）`],['missing',`意见不完整 ${counts.missing}`]]){const o=document.createElement('option');o.value=value;o.textContent=text;select.append(o)}
    select.value=filter;select.addEventListener('change',()=>{filter=select.value;draw();nav.querySelector('select')?.focus()});nav.append(select)
    const items=packet.items.filter(i=>filter==='all'||compareRoles(viewResult,i.itemId).kind===filter)
    if(!items.some(i=>i.itemId===selected)) selected=items[0]?.itemId||''
    for(const item of items){const button=el('button',`${item.itemId} · ${item.claim}`) as HTMLButtonElement;button.type='button';button.setAttribute('aria-pressed',String(selected===item.itemId));button.addEventListener('click',()=>{selected=item.itemId;draw();(nav.querySelector('button[aria-pressed=true]') as HTMLButtonElement)?.focus()});nav.append(button)}
    const item=packet.items.find(i=>i.itemId===selected)
    if(!item){detail.append(el('p','此筛选下没有主张；没有隐藏的自动裁决结果。'));return}
    const view=compareRoles(viewResult,item.itemId)
    detail.append(el('p',item.itemId,'eyebrow'),el('h2','人工编写测试主张（含反例）'),el('p',item.claim),el('p','这些主张由人工编写用于测试审读能力，不等于报告结论或已认定事实。','warning'),el('p',view.kind==='different'?'标签分歧 · 两侧意见并列保留':view.kind==='same'?'标签相同 · 不是共识或事实确认':'意见不完整 · 不能判定一致或分歧','badge'))
    const reportQuote=el('section',undefined,'report-quote');reportQuote.append(el('h3','固定报告逐字引用'),el('p','来自冻结报告文本片段的逐字引用；与下方模型选取引文分别展示。PDF 未重新认证。'),el('pre',item.citation.quote));detail.append(reportQuote)
    const columns=el('div',undefined,'columns')
    roles.forEach((role,index)=>{const card=el('article',undefined,'card');card.append(el('h3',ROLE_NAMES[index]),el('p',`${roleText[role.status]||role.status}（${role.status}） · 模型轮次 ${role.modelCalls}/4 · 工具 ${role.toolCalls}/8`),el('p','ticketId' in role?(role.ticketId||'尚未发行票据'):role.runId,'mono'));const review=view.reviews[index]
      if(review){card.append(el('h4',`建议标签：${review.label}`),el('p',review.rationale),el('h4','不确定性'),el('p',review.uncertainty),el('h4','模型选取引文（精确子串不代表语义正确）'),el('pre',review.quote))}
      else card.append(el('p','该角色没有已接受的完整意见，不补造答案。'))
      columns.append(card)
    });detail.append(columns)
    const source=el('details');source.append(el('summary','展开同页冻结报告文本片段与出处'))
    source.append(el('p',`PDF 第 ${item.sourceLocator.pdfPage} 页 / 印刷页 ${item.sourceLocator.printedPage} · ${item.sourceLocator.section}`),el('p',item.sourceLocator.url,'mono'),el('p',`PDF SHA-256（来源声明）：${item.sourceLocator.pdfSha256}`,'mono'),el('p',`片段 SHA-256：${item.sourceSha256}`,'mono'),el('pre',item.sourceText),el('p','公开报告来源声明，未重新下载或认证PDF。本页不打开外部链接。'))
    detail.append(source)
  }
  file.addEventListener('change',async()=>{
    const chosen=file.files?.[0];if(!chosen||meeting)return
    const own=++generation;status.textContent='正在本地校验；未上传。'
    try{
      if(chosen.size>MAX_BYTES)throw Error('文件超过 1 MiB 限额。')
      const bytes=new Uint8Array(await chosen.arrayBuffer());const next=parseResult(bytes)
      if(own!==generation)return
      result=next;filter='all';selected=packet.items[0].itemId;draw();status.textContent='已载入未核实结果；没有执行模型或确认事实。'
    }catch{if(own===generation)status.textContent='载入失败：结构、预算或冻结来源绑定不符合要求。此前结果保留；未上传、未自动重试。'}
    finally{if(own===generation)file.value=''}
  })
  clear.addEventListener('click',()=>{generation++;result=null;meeting=null;roundIndex=0;file.value='';filter='all';draw();status.textContent='已清空本页结果；未修改原始文件。'})
  draw()
}

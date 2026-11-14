import {packet, PACKET_SHA, MAX_BYTES, ROLE_NAMES, parseResult, mode, comparison, type Result} from './model'
export function mount(root:HTMLElement) {
  let result:Result|null=null, selected=packet.items[0].itemId, filter='all', generation=0
  const el=(tag:string,text?:string,className?:string)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n}
  const header=el('header');header.append(el('p','MCIS / PUBLIC RESEARCH','eyebrow'),el('h1','双视角审读工作台'),el('p','公开报告冻结片段 · 不是真人专家 · 全部意见未核实'))
  const notice=el('aside','仅在本地查看公开材料的结果 JSON。不接入案件、不运行模型、不上传。相同标签不是共识，分歧不自动裁决。','notice')
  const controls=el('section',undefined,'toolbar'),label=el('label','选入 a686c85 的 result.json（最大 1 MiB） '),file=document.createElement('input');file.type='file';file.accept='.json,application/json';label.append(file)
  const clear=el('button','清空结果') as HTMLButtonElement;clear.type='button';controls.append(label,clear)
  const status=el('p','尚未载入结果。只接受冻结 YANGZE 22 公开片段，不接受其他案例。');status.setAttribute('role','status');status.setAttribute('aria-live','polite')
  const provenance=el('section',undefined,'provenance'),body=el('div',undefined,'workspace'),nav=el('nav');nav.setAttribute('aria-label','主张选择')
  const detail=el('section');detail.setAttribute('aria-label','主张与双角色意见');body.append(nav,detail)
  root.replaceChildren(header,notice,controls,status,provenance,body)
  function draw(){
    provenance.replaceChildren();nav.replaceChildren();detail.replaceChildren()
    if(!result){detail.append(el('h2','准备审读'),el('p','从已保存的公开案例运行目录选入 result.json。此页不包含预置模型答案，也不会自动执行模型。'));return}
    const r=result
    provenance.append(el('h2',mode(r)),el('p',`运行状态：${r.status} / ${r.outcome} · 未核实`),el('p',`运行 ID：${r.runId}`,'mono'),el('p',`声明运行 Pi：${r.realPi} · 提供方请求次数：${r.providerRequests} · 模型：deepseek-v4-pro`),el('p',`来源包 SHA-256：${PACKET_SHA}`,'mono'),el('p','仅校验本地 JSON 结构与冻结来源绑定；未核验 completion.json 或回执链，不能证明导出完整、真实调用、作者或源PDF真实性。','warning'))
    if(r.errorCode) provenance.append(el('p',`未接受原因代码：${r.errorCode}`))
    const counts={same:0,different:0,missing:0};for(const item of packet.items) counts[comparison(r,item.itemId).kind as keyof typeof counts]++
    const select=document.createElement('select');select.setAttribute('aria-label','筛选意见状态')
    for(const [value,text] of [['all','全部主张'],['different',`标签分歧 ${counts.different}`],['same',`标签相同 ${counts.same}（非共识）`],['missing',`意见不完整 ${counts.missing}`]]){const o=document.createElement('option');o.value=value;o.textContent=text;select.append(o)}
    select.value=filter;select.addEventListener('change',()=>{filter=select.value;draw();nav.querySelector('select')?.focus()});nav.append(select)
    const items=packet.items.filter(i=>filter==='all'||comparison(r,i.itemId).kind===filter)
    if(!items.some(i=>i.itemId===selected)) selected=items[0]?.itemId||''
    for(const item of items){const button=el('button',`${item.itemId} · ${item.claim}`) as HTMLButtonElement;button.type='button';button.setAttribute('aria-pressed',String(selected===item.itemId));button.addEventListener('click',()=>{selected=item.itemId;draw();(nav.querySelector('button[aria-pressed=true]') as HTMLButtonElement)?.focus()});nav.append(button)}
    const item=packet.items.find(i=>i.itemId===selected)
    if(!item){detail.append(el('p','此筛选下没有主张；没有隐藏的自动裁决结果。'));return}
    const view=comparison(r,item.itemId)
    detail.append(el('p',item.itemId,'eyebrow'),el('h2',item.claim),el('p','待审主张，非已认定事实。','warning'),el('p',view.kind==='different'?'标签分歧 · 两侧意见并列保留':view.kind==='same'?'标签相同 · 不是共识或事实确认':'意见不完整 · 不能判定一致或分歧','badge'))
    const columns=el('div',undefined,'columns')
    r.roles.forEach((role,index)=>{const card=el('article',undefined,'card');card.append(el('h3',ROLE_NAMES[index]),el('p',`${role.status} · 模型轮次 ${role.modelCalls}/4 · 工具 ${role.toolCalls}/8`),el('p',role.runId,'mono'));const review=view.reviews[index]
      if(review){card.append(el('h4',`建议标签：${review.label}`),el('p',review.rationale),el('h4','不确定性'),el('p',review.uncertainty),el('h4','原文引用（精确子串，不代表语义正确）'),el('pre',review.quote))}
      else card.append(el('p','该角色没有已接受的完整意见，不补造答案。'))
      columns.append(card)
    });detail.append(columns)
    const source=el('details');source.append(el('summary','展开冻结原文与出处'))
    source.append(el('p',`PDF 第 ${item.sourceLocator.pdfPage} 页 / 印刷页 ${item.sourceLocator.printedPage} · ${item.sourceLocator.section}`),el('p',item.sourceLocator.url,'mono'),el('p',`PDF SHA-256（来源声明）：${item.sourceLocator.pdfSha256}`,'mono'),el('p',`片段 SHA-256：${item.sourceSha256}`,'mono'),el('pre',item.sourceText),el('p','公开报告来源声明，未重新下载或认证PDF。本页不打开外部链接。'))
    detail.append(source)
  }
  file.addEventListener('change',async()=>{
    const chosen=file.files?.[0];if(!chosen)return
    const own=++generation;status.textContent='正在本地校验；未上传。'
    try{
      if(chosen.size>MAX_BYTES)throw Error('文件超过 1 MiB 限额。')
      const bytes=new Uint8Array(await chosen.arrayBuffer());const next=parseResult(bytes)
      if(own!==generation)return
      result=next;filter='all';selected=packet.items[0].itemId;draw();status.textContent='已载入未核实结果；没有执行模型或确认事实。'
    }catch{if(own===generation)status.textContent='载入失败：结构、预算或冻结来源绑定不符合要求。此前结果保留；未上传、未自动重试。'}
    finally{if(own===generation)file.value=''}
  })
  clear.addEventListener('click',()=>{generation++;result=null;file.value='';filter='all';draw();status.textContent='已清空本页结果；未修改原始文件。'})
  draw()
}

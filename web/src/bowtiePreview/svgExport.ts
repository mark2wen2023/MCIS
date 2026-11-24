// Only the inline, React-created draft is accepted. Do not serialize surrounding page DOM.
const ns='http://www.w3.org/2000/svg'
const tags=new Set(['svg','defs','marker','path','line','g','rect','title','text','desc'])
const attributes=new Set(['role','aria-label','viewBox','id','markerWidth','markerHeight','refX','refY','orient','d','fill','x1','y1','x2','y2','stroke','marker-end','x','y','width','height','rx','font-size'])
const notices=[
 '人工 Bow-tie 假设草图 · 所有节点待核验 · 屏障 Unknown',
 '连线仅表达输入，非已证实因果、事实、责任或屏障有效性。',
 '参考资料不绑定节点，本文件不含原件、证据明细或结构核查结果。',
 '未找到端点的连线不绘制；完整节点 ID 保留在各节点标题中。',
]
export function serializeBowtieSvg(svg:SVGSVGElement):string {
 const copy=svg.cloneNode(true) as SVGSVGElement
 if(copy.namespaceURI!==ns||copy.localName!=='svg')throw Error('Unexpected diagram')
 // Fail closed if the inline drawing ever gains active or externally linked content.
 for(const node of [copy,...Array.from(copy.querySelectorAll('*'))]){
  if(node.namespaceURI!==ns||!tags.has(node.localName))throw Error('Unexpected SVG element')
  for(const a of Array.from(node.attributes)){
   if(a.namespaceURI||!attributes.has(a.name))throw Error('Unexpected SVG attribute')
   if(a.name==='marker-end'&&a.value!=='url(#w153-arrow)')throw Error('Unexpected marker')
   if((a.name==='fill'||a.name==='stroke')&&!/^#[0-9a-f]{6}$/i.test(a.value))throw Error('Unexpected color')
  }
 }
 const view=copy.getAttribute('viewBox')?.match(/^0 0 1270 ([0-9]+)$/)
 if(!view)throw Error('Unexpected diagram bounds')
 const height=Number(view[1])
 copy.setAttribute('viewBox',`0 0 1270 ${height+116}`)
 // Opaque background keeps the preview's light node labels readable standalone.
 const background=copy.ownerDocument.createElementNS(ns,'rect')
 background.setAttribute('width','1270');background.setAttribute('height',String(height+116))
 background.setAttribute('fill','#102b37');copy.prepend(background)
 for(const [i,label] of notices.entries()){
  const line=copy.ownerDocument.createElementNS(ns,'text')
  line.setAttribute('x','18');line.setAttribute('y',String(height+24+24*i))
  line.setAttribute('font-size','16');line.setAttribute('fill','#ecf6fa');line.textContent=label
  copy.append(line)
 }
 const xml=new XMLSerializer().serializeToString(copy)
 for(const ch of xml){const c=ch.codePointAt(0)!;if(c<32&&c!==9&&c!==10&&c!==13||c>=0xd800&&c<=0xdfff||c===0xfffe||c===0xffff)throw Error('Invalid XML character')}
 return xml
}
export function downloadBowtieSvg(svg:SVGSVGElement):void {
 const url=URL.createObjectURL(new Blob([serializeBowtieSvg(svg)],{type:'image/svg+xml;charset=utf-8'}))
 const anchor=svg.ownerDocument.createElement('a')
 try{anchor.href=url;anchor.download='bowtie-draft.svg';svg.ownerDocument.body.append(anchor);anchor.click()}
 finally{anchor.remove();setTimeout(()=>URL.revokeObjectURL(url),0)}
}

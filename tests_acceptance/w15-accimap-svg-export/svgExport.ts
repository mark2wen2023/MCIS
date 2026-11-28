// Isolated local AcciMap SVG export helper. Not wired into the product preview or official routes.
const SVG_NS = 'http://www.w3.org/2000/svg'

function assertSafeXml(xml: string): void {
  for (const ch of xml) {
    const c = ch.codePointAt(0)!
    if ((c < 32 && c !== 9 && c !== 10 && c !== 13) || (c >= 0xd800 && c <= 0xdfff) || c === 0xfffe || c === 0xffff) {
      throw new Error('Invalid XML character')
    }
  }
}

/** Serialize the already-rendered six-layer sketch SVG without changing the preview component. */
export function serializeAcciMapSvg(svg: SVGSVGElement): string {
  const copy = svg.cloneNode(true) as SVGSVGElement
  copy.setAttribute('xmlns', SVG_NS)
  const xml = new XMLSerializer().serializeToString(copy)
  assertSafeXml(xml)
  return xml
}

export function downloadAcciMapSvg(svg: SVGSVGElement): void {
  const url = URL.createObjectURL(new Blob([serializeAcciMapSvg(svg)], { type: 'image/svg+xml;charset=utf-8' }))
  const anchor = svg.ownerDocument.createElement('a')
  try {
    anchor.href = url
    anchor.download = 'accimap-synthetic-draft.svg'
    svg.ownerDocument.body.append(anchor)
    anchor.click()
  } finally {
    anchor.remove()
    setTimeout(() => URL.revokeObjectURL(url), 0)
  }
}

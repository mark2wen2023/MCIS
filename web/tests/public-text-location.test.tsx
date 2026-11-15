import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { renderToStaticMarkup } from 'react-dom/server'
import { PublicTextLocation, publicTextLocation } from '../src/reports/PublicTextLocation'
import index from '../src/reports/publicTextIndex.json'
import type { Citation } from '../src/reports/types'
// Real public source bytes; rejection inputs are constructed, not model results.
const raw=readFileSync('../reports/yangze22/report.txt'), lines=raw.toString('utf8').split('\n')
assert.equal(createHash('sha256').update(raw).digest('hex'),index.sha256)
assert.equal(lines.length,index.lineCount)
const pageAt=(line:number)=>lines.slice(0,line).join('\n').split('\f').length
function citation(start:number,end:number):Citation {
 const ps=pageAt(start),pe=pageAt(end)
 return {kind:'evidence',id:'EV-201',href:`#/evidence?id=EV-201&case=${index.caseId}`,registration:'registered',unregistered:false,needsReview:true,
 sourceRef:`${index.path}#L${start}-L${end}; SHA256=${index.sha256}; PDF页=${ps}–${pe}; 正文页=${ps-2}–${pe-2}`}
}
let checks=0
const ok=(v:unknown)=>{assert.ok(v);checks++}
const c=citation(1026,1033)
ok(lines.slice(1025,1033).join('\n').includes('主要责任'))
ok(publicTextLocation(c,index.caseId)?.href.endsWith('#L1026-L1033'))
ok(publicTextLocation(c,index.caseId)?.href.includes(index.commit))
const repeated=new Map<string,number[]>()
lines.forEach((line,i)=>{if(line.trim().length>=5&&pageAt(i+1)>=3)repeated.set(line,[...(repeated.get(line)||[]),i+1])})
const pair=[...repeated.values()].find(values=>values.length>1)!
ok(!!pair)
ok(publicTextLocation(citation(pair[0],pair[0]),index.caseId)?.href!==publicTextLocation(citation(pair[1],pair[1]),index.caseId)?.href)
const boundary=index.pageBreakLines.find(n=>pageAt(n-1)>=3)!
const cross=publicTextLocation(citation(boundary-1,boundary+1),index.caseId)!
ok(cross.pageEnd>cross.pageStart)
ok(cross.start===boundary-1&&cross.end===boundary+1)
for(const bad of [
 {...c,id:'EV-202'},{...c,kind:'recommendation' as const},{...c,registration:'unregistered' as const},{...c,unregistered:true},
 {...c,href:'#/evidence?id=EV-201&case=OTHER'},{...c,href:c.href+'&case='+index.caseId},{...c,href:'https://example.com'},
 {...c,sourceRef:c.sourceRef!.replace(index.sha256,'a'.repeat(64))},
 {...c,sourceRef:c.sourceRef!.replace('PDF页=49–49','PDF页=48–49')},
 {...c,sourceRef:c.sourceRef!.replace('L1026-L1033','L1033-L1026')},
 {...c,sourceRef:c.sourceRef!.replace('L1026-L1033','L1026-L999999')},
 {...c,sourceRef:c.sourceRef!+'\n<script>bad</script>'},{...c,sourceRef:undefined},{...c,sourceRef:c.sourceRef!+'\n'},
])ok(publicTextLocation(bad,index.caseId)===null)
ok(publicTextLocation(c,'OTHER')===null)
const html=renderToStaticMarkup(<PublicTextLocation citation={c} caseId={index.caseId}/>)
ok(html.includes('L1026–L1033'))
ok(html.includes('非 PDF 跳页')&&html.includes('不是当前证据原件核验'))
ok(html.includes('noopener noreferrer'))
ok(renderToStaticMarkup(<PublicTextLocation citation={c} caseId="OTHER"/>)==='')
// Actual terminal separator: never label it PDF54, nor silently clamp to PDF53.
assert.equal(lines[1155], '\f')
ok(publicTextLocation(citation(1156,1156),index.caseId)===null)
ok(publicTextLocation(citation(1155,1156),index.caseId)===null)
ok(publicTextLocation({...citation(1156,1156),sourceRef:citation(1156,1156).sourceRef!.replace('54–54','53–53').replace('52–52','51–51')},index.caseId)===null)
ok(publicTextLocation(citation(1155,1155),index.caseId)?.pageEnd===53)
// Blank physical lines retain their real page; they do not create/remove pages.
const blank=lines.findIndex((line,i)=>i>100&&!line.trim()&&!line.includes('\f'))+1
ok(publicTextLocation(citation(blank,blank),index.caseId)?.pageStart===pageAt(blank))
const physicalPages=raw.toString('utf8').split('\f')
assert.equal(physicalPages.pop(),'') // only the terminal fragment is discarded
assert.equal(physicalPages.length,index.pdfPageCount)
assert.equal(physicalPages.filter(page=>!page.trim()).length,0) // no actual empty PDF page claimed tested
for(const b of index.pageBreakLines.filter(n=>n<1156&&pageAt(n-1)>=3)) {
 const location=publicTextLocation(citation(b-1,b+1),index.caseId)
 assert.ok(location)
 assert.equal(location.pageStart,pageAt(b-1))
 assert.equal(location.pageEnd,pageAt(b+1))
}
ok(renderToStaticMarkup(<PublicTextLocation citation={citation(1156,1156)} caseId={index.caseId}/>)==='')
console.log(`${checks} public text location assertions passed (actual source + constructed rejection/SSR; no browser)`)

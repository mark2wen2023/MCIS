import assert from 'node:assert/strict'
import {renderToStaticMarkup} from '../../web/node_modules/react-dom/server'
import {OpaqueUploadStatus} from '../../web/src/evidenceIntake/OpaqueUploadStatus'
import {uploadFileNameValid,fileNameValid,parseReceipt} from '../../web/src/evidenceIntake/model'
import type {EvidenceItem} from '../../web/src/types'
const path='raw/evidence-intakes/'+'a'.repeat(64)+'/source.bin'
const item={caseId:'SYN',evidenceId:'<script>bad()</script>',category:'<img src=x onerror=bad()>',relativePath:path} as EvidenceItem
const html=(changes:Partial<EvidenceItem>={})=>renderToStaticMarkup(<OpaqueUploadStatus caseId="SYN" evidence={{...item,...changes}}/>)
let count=0
for(const relativePath of [path+'\n',path+'\r',path+'\r\n',path+'/more',' '+path,path.replace('a'.repeat(64),'A'.repeat(64)),path.replace('source.bin','sourceXbin')]){
 assert.equal(html({relativePath}),'',JSON.stringify(relativePath));count++
}
assert.equal(html({caseId:'OTHER'}),'');count++
const shown=html()
assert.ok(shown.includes('&lt;script&gt;'));count++
assert.ok(shown.includes('&lt;img'));count++
assert.ok(!/<(?:script|img|iframe|video|audio)\b/.test(shown));count++
for(const code of [0x61c,0x200e,0x200f,0x202a,0x202b,0x202c,0x202d,0x202e,0x2066,0x2067,0x2068,0x2069]){
 const name='old'+String.fromCodePoint(code)+'file.bin'
 assert.equal(fileNameValid(name),true);assert.equal(uploadFileNameValid(name),false);count++
}
for(const name of ['تقرير.pdf','照片😀.png','report\u0301.pdf']){assert.equal(uploadFileNameValid(name),true);count++}
const metadata={title:'synthetic',source:'synthetic',extractedBy:'synthetic',extractedUtc:'2026-01-01T00:00:00Z',category:'Other',confidentiality:'Restricted',note:''}
const legacy={caseId:'SYN',evidenceId:'EV-1',requestDigest:'a'.repeat(64),sourceSha256:'b'.repeat(64),fileName:'old\u202efile.bin',byteLength:0,metadata,registeredUtc:'2026-01-01T00:00:00Z',registeredBy:'synthetic',registeredRole:'Investigator',replayed:true,evidence:{...metadata,caseId:'SYN',evidenceId:'EV-1',sha256:'b'.repeat(64),status:'Unverified',accessCount:0}}
assert.equal(parseReceipt(legacy,'SYN').fileName,legacy.fileName);count++
for(const relativePath of [null,undefined,42,{}]){assert.equal(html({relativePath} as unknown as Partial<EvidenceItem>),'');count++}
assert.ok(shown.includes('保存结果请核对登记回执'));count++
console.log(`${count} independent opaque upload frontend assertions passed; React server rendering, no browser`)

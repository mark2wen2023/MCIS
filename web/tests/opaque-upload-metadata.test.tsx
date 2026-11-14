import assert from 'node:assert/strict'
import {renderToStaticMarkup} from 'react-dom/server'
import {OpaqueUploadStatus} from '../src/evidenceIntake/OpaqueUploadStatus'
import {uploadFileNameValid,fileNameValid,intakeBody,type Metadata} from '../src/evidenceIntake/model'
import type {EvidenceItem} from '../src/types'
let n=0
const controls=[0x61c,0x200e,0x200f,...Array.from({length:5},(_,i)=>0x202a+i),...Array.from({length:4},(_,i)=>0x2066+i)]
const meta:Metadata={title:'Synthetic',source:'Synthetic',extractedBy:'Synthetic',extractedUtc:'2026-01-01T00:00:00Z',category:'Photo',confidentiality:'Restricted',note:''}
for(const c of controls){const name='photo'+String.fromCharCode(c)+'gpj.exe';assert.equal(uploadFileNameValid(name),false);assert.equal(fileNameValid(name),true);assert.throws(()=>intakeBody(name,'',meta));n++}
for(const name of ['照片 😀.png','تقرير.pdf','report\u0301.pdf']){assert.equal(uploadFileNameValid(name),true);assert.equal(intakeBody(name,'',meta).fileName,name);n++}
const evidence:EvidenceItem={caseId:'SYN',evidenceId:'EV-001',title:'Synthetic',source:'Synthetic',extractedBy:'Synthetic',extractedUtc:'2026-01-01T00:00:00Z',sha256:'a'.repeat(64),relativePath:'raw/evidence-intakes/'+'a'.repeat(64)+'/source.bin',confidentiality:'Restricted',category:'Photo',status:'Unverified',needsReview:false,currentSha256:'a'.repeat(64),accessCount:0}
const render=(e:EvidenceItem|undefined,caseId='SYN')=>renderToStaticMarkup(<OpaqueUploadStatus caseId={caseId} evidence={e}/>)
for(const status of ['Unverified','Verified','Mismatch','NeedsReview'] as const){const html=render({...evidence,status});assert.match(html,/实际文件类型未验证/);assert.match(html,/未执行 OCR/);assert.match(html,/字节一致不等于理解内容/);assert.doesNotMatch(html,/<img|<iframe|<video|<audio|<object|<script/);n++}
for(const path of [undefined,'raw/photo.png',evidence.relativePath+'\n',evidence.relativePath+'\r\n','raw/evidence-intakes/'+'A'.repeat(64)+'/source.bin','raw/evidence-intakes/'+'a'.repeat(64)+'/source.bin/extra']){assert.equal(render({...evidence,relativePath:path}),'');n++}
assert.equal(render(evidence,'OTHER'),'');assert.equal(render(undefined),'');n+=2
const html=render({...evidence,category:'<img src=x onerror=alert(1)>',evidenceId:'<script>bad</script>'})
assert.doesNotMatch(html,/<img|<script/);assert.match(html,/&lt;img/);n++
console.log(`${n} opaque-upload metadata/render checks passed (SSR, no browser)`)

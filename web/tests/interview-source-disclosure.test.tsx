import assert from 'node:assert/strict'
import { renderToStaticMarkup } from 'react-dom/server'
import { SourceDisclosure } from '../src/interview/SourceDisclosure'
const html=(props:Parameters<typeof SourceDisclosure>[0])=>renderToStaticMarkup(<SourceDisclosure {...props}/> )
const missing=html({caseId:'SYNTHETIC'})
assert.ok(missing.includes('未提供原件证据编号') && missing.includes('未提供来源 SHA-256'))
assert.ok(!missing.includes('<a ') && missing.includes('字段未返回不等于原始资料不存在'))
assert.ok(html({caseId:'SYNTHETIC',evidenceId:null,sourceSha256:null}).includes('未提供来源 SHA-256'))
const sha='Ab'.repeat(32)
const complete=html({caseId:'CASE & # 中文',evidenceId:'EV-009',sourceSha256:sha})
assert.ok(complete.includes(sha) && complete.includes('待人工核对'))
assert.ok(complete.includes('#/evidence?case=CASE+%26+%23+%E4%B8%AD%E6%96%87&amp;id=EV-009'))
assert.ok(complete.includes('未读取或核验原件') && complete.includes('不代表 OCR/AI 已解析'))
for(const id of ['../private','EV-1&case=other','<script>synthetic</script>','EV-x']){
 const value=html({caseId:'SYNTHETIC',evidenceId:id,sourceSha256:sha})
 assert.ok(!value.includes('<a ') && value.includes('未生成证据链接'))
 assert.ok(!value.includes('<script>'))
}
for(const sourceSha256 of ['g'.repeat(64),'a'.repeat(63),'a'.repeat(65),'<script>']){
 const value=html({caseId:'SYNTHETIC',evidenceId:'EV-001',sourceSha256})
 assert.ok(value.includes('格式异常') && !value.includes('<script>'))
}
assert.ok(!html({caseId:' ',evidenceId:'EV-001',sourceSha256:sha}).includes('<a '))
assert.ok(!html({caseId:'SYNTHETIC',sourceSha256:sha}).includes('<a '))
assert.ok(html({caseId:'SYNTHETIC',sourceSha256:sha}).includes(sha)) // hash alone never fabricates evidence identity
assert.ok(html({caseId:'SYNTHETIC',evidenceId:'  ',sourceSha256:'  '}).includes('未提供'))
console.log('Interview source disclosure synthetic SSR checks passed; no file/API/model calls')

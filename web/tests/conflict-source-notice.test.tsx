// SSR and existing synthetic edit helpers, not browser or permission verification.
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {renderToStaticMarkup} from 'react-dom/server'
import {SourceReviewNotice} from '../src/timeline/SourceReviewNotice'
import {conflictWriteBody} from '../src/timeline/conflictEditing'
const html=renderToStaticMarkup(<SourceReviewNotice />)
for(const text of ['来源复核说明','处理记录与来源核验分开','不表示已核验来源版本或原件','未记录您阅读时的证据版本','不会生成已读证明','可按现有权限保留处理说明','具备相应权限的调查员复核']) assert.ok(html.includes(text),text)
assert.ok(!html.includes('title=')) // Guidance is visible text, not hover-only.
assert.ok(!html.includes('button')&&!html.includes('input')) // No fake confirmation action.
const source=readFileSync('src/pages/EvidencePage.tsx','utf8')
assert.ok(source.includes('<SourceReviewNotice />'))
assert.ok(source.includes('处理状态（非来源核验）'))
assert.ok(source.includes('if(sent) { setDrafts(current => acknowledgeDraft(current,c.conflictId,sent))'))
assert.deepEqual(conflictWriteBody('a'.repeat(64),{resolution:'Synthetic pending review'}),{resolution:'Synthetic pending review',expectedVersion:'a'.repeat(64)})
console.log('13 SSR/workflow assertions passed; no browser or source verification')

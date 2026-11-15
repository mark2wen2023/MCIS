// Synthetic state sequences and wiring checks, not browser or HTTP tests.
import {strict as assert} from 'node:assert'
import {readFileSync} from 'node:fs'
import {selectDraft,changeDraft,acknowledgeDraft,compareDraft,type EditableConflict} from '../src/timeline/conflictEditing'
const old='a'.repeat(64),next='b'.repeat(64)
const a={conflictId:'C-01',resolution:'server A',expectedVersion:old} as EditableConflict
const b={...a,conflictId:'C-02',resolution:'server B'}
const updated={...a,resolution:'other user saved',expectedVersion:next}
let d=changeDraft({},a,'local unsaved text')
const sent=d[a.conflictId]
// After 412/refresh/reselection neither draft text nor original version changes.
assert.equal(selectDraft(d,updated),d)
d=selectDraft(d,b);d=selectDraft(d,updated)
assert.equal(d[a.conflictId].note,'local unsaved text')
assert.equal(d[a.conflictId].version,old)
// Status success never clears drafts, including another record's draft.
assert.equal(acknowledgeDraft(d,a.conflictId,undefined),d)
assert.equal(acknowledgeDraft(d,b.conflictId,undefined),d)
d=changeDraft(d,a,'newer typing')
assert.equal(acknowledgeDraft(d,a.conflictId,sent),d)
d=compareDraft(d,updated)
assert.equal(d[a.conflictId].note,'newer typing')
assert.equal(d[a.conflictId].version,next)
const accepted=d[a.conflictId]
d=acknowledgeDraft(d,a.conflictId,accepted)
assert.equal(d[a.conflictId],undefined)
assert.equal(d[b.conflictId].note,'server B')
const source=readFileSync('src/pages/EvidencePage.tsx','utf8')
assert.ok(source.includes('setDrafts(current => selectDraft(current,c))'))
assert.ok(source.includes('if(sent) { setDrafts(current => acknowledgeDraft(current,c.conflictId,sent))'))
assert.ok(!source.includes('setEditing(null); onChanged()'))
assert.ok(source.includes('setDrafts(current => compareDraft(current,c))'))
assert.ok(source.includes('离开页面或重新加载网页不保留'))
console.log('15 synthetic draft-state/wiring assertions passed; browser not tested')

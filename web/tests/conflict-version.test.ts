// Constructed transport-body tests, not browser interaction.
import {strict as assert} from 'node:assert'
import {editableRows,conflictWriteBody,CONFLICT_REFRESH_NOTICE} from '../src/timeline/conflictEditing'
import type {Conflict} from '../src/types'
const old='a'.repeat(64),next='b'.repeat(64)
const conflict={conflictId:'C-01',resolution:'Saved'} as Conflict
const row=editableRows([{conflict,version:old}])[0]
const editingVersion=row.expectedVersion
assert.equal(editableRows([{conflict,version:next}])[0].expectedVersion,next)
assert.equal(conflictWriteBody(editingVersion,{resolution:'Local draft'}).expectedVersion,old)
assert.equal(conflictWriteBody(editingVersion,{resolution:'Local draft'}).resolution,'Local draft')
assert.throws(()=>conflictWriteBody(undefined,{resolution:'Local draft'}))
assert.throws(()=>editableRows([{conflict,version:'*'}]))
for(const word of ['本地说明尚未保存','刷新比对','不会自动重试'])assert.ok(CONFLICT_REFRESH_NOTICE.includes(word))
console.log('8 synthetic conflict-version assertions passed; browser not tested')

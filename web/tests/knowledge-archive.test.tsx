import assert from 'node:assert/strict'
import React from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {summary,archive,saved,detail} from '../src/knowledgeArchive/model'
import {SummaryView} from '../src/knowledgeArchive/Panel'
const s={profile:'MCIS-KNOWLEDGE-ARCHIVE-1',archiveSha256:'a'.repeat(64),byteLength:2,cardCount:0,auditCount:0,auditHeadSha256:'0'.repeat(64),auditSnapshotCount:0,snapshotCoverage:{mode:'legacy-only',firstSeq:null,priorHeadSha256:'0'.repeat(64)},scope:'current-online-library-snapshot',restoreMode:'isolated-read-only-history',identityMode:'unverified-self-reported'}
assert.equal(summary(s),s)
assert.throws(()=>summary({...s,extra:true}))
assert.throws(()=>summary(s,'b'.repeat(64)))
assert.throws(()=>summary({...s,byteLength:8388609}))
assert.throws(()=>summary({...s,cardCount:true}))
assert.throws(()=>summary({...s,auditSnapshotCount:1}))
assert.throws(()=>summary({...s,snapshotCoverage:{...s.snapshotCoverage,mode:'from-sequence',firstSeq:1}}))
const a={summary:s,importedUtc:'2026-11-12T00:00:00Z',importedBy:'Synthetic',importedRole:'LeadInvestigator'}
assert.equal(archive(a),a)
assert.throws(()=>archive({...a,importedRole:'Investigator'}))
assert.equal(saved({archive:a,replayed:true},s.archiveSha256),a)
assert.throws(()=>saved({archive:a,replayed:'yes'},s.archiveSha256))
assert.throws(()=>detail({archive:a,envelope:{}},s.archiveSha256))
assert.match(renderToStaticMarkup(<SummaryView value={summary(s)}/>),/丢失信息为未知/)
console.log('knowledge archive: 13 assertions passed')
import {ArchiveError,definitelyRejected} from '../src/knowledgeArchive/api'
assert.equal(definitelyRejected(new ArchiveError(403,'FORBIDDEN')),false)
assert.equal(definitelyRejected(new ArchiveError(403,'FORBIDDEN',true)),true)
assert.equal(definitelyRejected(new ArchiveError(422,'FORBIDDEN',true)),false)
assert.equal(definitelyRejected(new ArchiveError(503,'KNOWLEDGE_ARCHIVE_UNAVAILABLE',true)),true)
assert.equal(definitelyRejected(new ArchiveError(404,'KNOWLEDGE_ARCHIVE_NOT_FOUND',true)),false)
console.log('write outcome marker: 5 assertions passed')

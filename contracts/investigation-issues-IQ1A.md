# IQ-1A manual persistent issue API (draft implementation contract)
Base: main 3aba2bf. API-only increment, no browser/UI/LLM or legal sign-off. Local role headers remain unverified identity. Authorize Investigator/LeadInvestigator via conservative full-content policy (all categories ReadOnly/ReadWrite, no applicable redaction; report_draft ReadWrite on mutations). Default Investigator is consequently denied. AgentService and all external roles denied. No new privilege escalation.
Prefix `/api/v1/cases/{caseId}/investigation-issues`. Responses including errors: no-store. Unknown keys rejected. No PATCH/DELETE.
- POST empty suffix: `{requestId:UUID,title:1..200,description:1..4000,sourceRefs:[],acknowledgeArchiveUnsupported:true}` → 201 `{issueId,revision:1,event}`; exact same request returns historical operation receipt 200, not latest view.
- GET empty suffix: `offset>=0,limit=1..50(default20)` → `{items,nextOffset}`. Offset pagination is this limited slice; no stable concurrent pagination claim.
- GET `/{issueId}` → current state, sourcesStale, archiveSupported=false and identityMode; ETag revision.
- GET `/{issueId}/events?after=0&limit=50` → ordered `{items,nextAfter}` (limit1..100).
- POST `/{issueId}/events`: `{requestId:UUID,expectedRevision:positiveInt,type,payload}` → `{issueId,revision,event}`. bool not integer. Server-generated actor, role, UTC and sequence. Replay bound to case/role/operator/request and identical normalized request including issueId; changed content→409 REQUEST_REUSE. Revision mismatch→409. Every write uses SQLite reserved transaction; event, state and receipt commit together. Event/receipt tables reject update/delete. No signed or tamper-proof identity claim.
SourceRef = `{evidenceId:EV-NNN,sha256:lowerhex64}` ≤20 unique, existing accessible evidence in same case; current SHA required on write. This is evidence registry content hash binding, not byte verification or scientific truth. No arbitrary URLs. No page/clip locators yet. Missing/restricted history sources fail closed for whole issue rather than selective redaction. Current SHA changes mark stale on reads; old events remain.
States: Observed, AssessmentRecorded, Verifying, AwaitingDiscussion, DiscussionRecorded.
Events:
- RecordHypothesis: `{hypothesisId:UUID,expectedVersion:0 for new or latest version,text,reason,sourceRefs}`. Allowed before DiscussionRecorded; generates new hypothesis version, resets current verification/packet (preserves history), enters AssessmentRecorded. Up to30 hypotheses.
- ReviewSources: `{sourceRefs,reason}`; replaces initial source snapshot with history preserved, resets current verification/packet, allowed before DiscussionRecorded. Also revise affected hypothesis references. Never changes original evidence.
- BeginVerification: `{question,method}` from AssessmentRecorded with≥1 hypothesis; starts fresh round.
- RecordVerification: `{hypothesisId,hypothesisVersion,activity,result,outcome,sourceRefs}` from Verifying; outcome Supported/Contradicted/Inconclusive/UnableToVerify. Result required even if unable. Binds current hypothesis version and current round. Does not adjudicate facts.
- SubmitDiscussion: `{agenda,unresolved:[strings]}` only when each current hypothesis has current-round verification; all currently relied-on sources must still match. Saves immutable packet in event. Allows Inconclusive/UnableToVerify, not forced agreement.
- RecordDiscussion: `{packetRevision,summary,dissent:[strings],participantsRecorded:[nonempty strings],outcome}`; outcome OpinionRecorded/MoreVerification/Undetermined. Participants are recorder's descriptions, NOT signatures or votes. MoreVerification opens new round and cannot reuse previous verification.
- Reopen: `{reason}` from DiscussionRecorded; resets current verification/packet with all history preserved.
All text fields except title ≤4000 unless string-list members≤1000; lists≤30. Request streamed byte cap64KiB, JSON structural limits depth16/nodes5000 after parsing; reject duplicates/nonfinite/invalidUnicode. 200 issues/case, 500 events/issue, limits reject not truncate. Source/version conflict409; auth403; absent case/issue404; malformed422; budget413. Error does not echo submitted text.

## Archive boundary
Saving any issue/event/receipt blocks case .mcase export with 409 ISSUE_ARCHIVE_UNSUPPORTED after full-content authorization. No issue restore implemented, no deletion to unlock export. Existing protection is extended to legacy and working-record exports; do not put issue tables on an allowlist. Create requires explicit acknowledgment of this restriction. Separate DB backup is outside this API and not implemented.

## Limits and acceptance
No UI, browser run, actual auth, report integration, cross-case import, archive restore, AI, evidence extraction or time calibration. Source SHA may be unchanged despite metadata changes; current source access is always rechecked. Single-host SQLite, not multi-server distributed validation. Requires independent API tests for source staleness/denial, roles, history, persistence/restart, atomic rollback, concurrent revisions/idempotency, archive refusal and multi-hypothesis/reverification coverage before merge. Current status: candidate, not production acceptance.

Issue events are the audit record for this slice, separate from general GET /audit. No claim of global audit UI integration.

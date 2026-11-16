# Media archive member/index proposal — research v1

Status: **offline research only; restore_ready=false**. This is NOT a new MCIS-MCASE packageVersion and is not recognized by product import/export. Existing whole-case refusal stays in force. No permissions, registered originals, active receipts, worker queues or product routes change.

## Input and retained members

The Python prototype `research/media_archive/contract.py::validate(index, payloads)` accepts an explicit index and an in-memory mapping of member IDs to bytes. It has no filesystem, ZIP, SQLite, network, model or worker access. Member IDs are identifiers, not paths. Every provided member must be indexed, length/hash matched and referenced; absent, unexpected or inconsistent members reject. Budgets:512 members,16MiB/member,64MiB aggregate. These are research limits, not a change to product upload limits. JSON uses UTF-8, duplicate keys/nonfinite constants reject. Member bytes are retained unchanged; the function does not rewrite or recalculate stored historical documents.

Top-level exact fields:
```text
format = MCIS-MEDIA-ARCHIVE-RESEARCH-1
caseId
restoreReady = false
taskPolicy = inactive-history-never-execute
members: { memberId: { size, sha256 } }
sources: [source]
runs: [run]
tasks: [task]
audit: [{ caseId, seq, member }]
```

| Record | Required fields and meaning |
|---|---|
| source | id, caseId, kind (`pdf`, `page-image`, `audio`), evidenceId, receiptMember, originalMember, registeredSha256, currentSha256, location |
| page-image location | pdfSourceId, pdfPage1Based (positive integer), printedPage (string or null), mappingBasis=`manual-declaration-not-verified`, width, height |
| audio location | frameCount, sampleRateHz, channels, sampleWidthBytes; positive exact integers. Duration is frameCount/sampleRateHz, not an integral-ms replacement. |
| pdf location | null; no inference of page count or render ancestry |
| run | id, caseId, sourceId, initialMember, machineMember, rawMember, recognizerMember, historyStatus, revisions, taskId (or null for offline import) |
| revisions | contiguous revision0..N; each {revision, member, auditSeq}. revision0 references initialMember. All recorded revisions required, not only the latest value. |
| historyStatus | `captured-from-initial` or `prior-history-unknown`; neither proves earlier nonexistent history. Missing captured initial or intermediate revisions reject, not invented. |
| task | id, caseId, sourceId, recordMember, recordedStatus, runId, auditSeqs, executionPolicy=`never` |

`receiptMember` preserves the registered receipt as an inactive historical document, never an active intake credential. Original bytes must agree with both named digests in this bounded proposal; a changed/missing original rejects rather than substituting a newer version. That agreement proves byte association only, not historical authenticity, author identity, or permission to read/export. Future extraction must use the existing authorization checks for all members and include existing evidence/custody history, not trust the archive's declared role or receipt.

`initialMember` is the complete saved revision-zero document, `machineMember` the complete saved machine artifact, `rawMember` complete raw recognizer JSON, and `recognizerMember` retained version/parameter/model metadata. Image initial.candidate or audio initial.machineDraft must equal the machine member. Image PDF/image/raw digests and declared PDF page must match the associated source. Audio exact frame/rate/current digest and raw-result digest must match. The prototype does not decode media, verify PDF page count, derive geometry, execute original machine-contract validation or authenticate model execution. Recognizer metadata is a recorded declaration; unknown version information must remain explicitly unknown in retained metadata, not fabricated.

Human revisions retain the entire native document including operator/role/time/reason, text/status and line/segment association. Prototype checks contiguous version numbers and expectedRevision, factVerified=false, required provenance, image line bounds, and audio unknown versus operator-declared exact-frame-bounded millisecond ranges. Unknown speaker stays unknown. It does not promote model emotion/VAD labels, OCR text or transcription_checked to facts. Full native machine/segment semantic validation is a future adapter prerequisite; no standalone index validation establishes restoration readiness.

## Tasks and audit

Recorded status is preserved as one of succeeded, failed, running_or_unknown, interrupted_unknown. Historical running/unknown is never interpreted as work to resume, safe failure, or success. All tasks have executionPolicy=never regardless of recorded status. A successful task must link the run reciprocally, with matching source and complete native raw/candidate results and their saved digests. Image Base64 artifacts retain their original decoded bytes; audio task JSON results are structurally matched to retained JSON members. Non-successful tasks have no published run; their complete task documents (including any existing errors) remain retained. No worker recovery/retry function exists.

Audit members retain the complete original case audit lines, sequence and previous-line SHA chain, not reconstructed summaries. Index checks case-scoped linkage and the expected action/command for each revision/task. **This is not yet proof of a unique native database row↔audit-event association:** current revision tables do not persist auditSeq foreign keys. A production extraction adapter must prove uniqueness using original stored events and revision content; absent/ambiguous mapping must reject, never guess. The prototype does not authenticate the chain or declare imported actor identities trustworthy.

## Known compatibility and admission blockers

- This branch contains the audio candidate; image candidate91962113 was read via Git only, not merged or executed.
- Audio v2 without retained raw recognizer JSON cannot satisfy this proposal and is rejected. No raw output is reconstructed from transcription text. v3/offline OCR still need extraction adapters and native-contract validation.
- The proposed member graph cannot prove that a caller supplied **all database rows**. A transactionally consistent exporter must enumerate source registrations/custody, every run/revision/task and whole-case audit, establish unique associations, and refuse any unrepresented state. That exporter does not exist in this slice.
- Imported receipts must not be restored into active intake tables. Existing media readers call live `load_receipt`; therefore the current product read path is not compatible with this proposal yet.
- Existing file publication/DB commit, readiness gating, uncertain outcome/restart protocol and all entrance checks remain prerequisites. No SQL/schema migration, publication, task reactivation or formal restore is implemented.
- Preserve unsupported-combination whole-package refusal. No table whitelist addition, original file mutation, inferred older history, or conversion of a prior declaration into new human approval.

Next bounded work after independent review: implement a read-only consistent extraction adapter for one native media mode, verify exact row/audit associations and complete inventories against temporary synthetic stores. Keep product restore refused until full multi-generation restore, compatibility, rollback/publication and independent review are complete.

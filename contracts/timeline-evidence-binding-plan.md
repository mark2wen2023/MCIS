# Timeline evidence-version binding: reviewed implementation plan

Status: design and current-model checks only. No operational binding endpoint,
trusted receipt table, UI, source approval or production authorization added.
Base inspected:877cfb4dbe9db0be9abba5231a79a3cdd23c7d88 (PR56).

## Existing facts and blockers
- timeline/align-preview consumes caller inline CSV, not a trusted EvidenceRow.
- AgentDraft payload is arbitrary JSON. Its citation contract requires quote,
  not necessarily a registered evidenceId. A quote is not authority or proof.
- package/mcase.py imports agents/drafts.json directly to AgentDraftRow.
  Rejecting caller snapshot fields only on submit does NOT cover package import.
- EvidenceRow.sha256 is registration-time. Custody Change changes currentSha256;
  Review clears a flag, not observation accuracy approval; Verify is hash checking.
- working_records_archive rejects populated unknown tables. Adding a receipt
  table without archive semantics can block backup; whitelisting and omitting
  it silently would be wrong. Existing generic agents are not covered by that
  restricted working-record archive either.

## Smallest safe operational slice selected for next implementation
Scope: server-owned binding for NEW timeline drafts referring to explicitly
registered evidence. This is version/lineage binding, not automatic observation
approval. Do not replace the current API with a toy evidence repository.

1. Use a separate server-owned local receipt, not a payload hash or a boolean.
   Bind case identity, draft identity, canonical draft/citations, exact evidence
   ID set, current registered/custody version and case epoch. Receipt creation
   is internal to authorized submission; accept no caller-controlled approval.
   Never expose a generic write/import endpoint for this receipt.
2. For byte-level claims, read bounded regular files under the case storage root
   with symlink-aware checks and compute the actual hash. Registration/current
   hashes alone do not establish actual bytes. Missing bytes mean unavailable,
   not successful binding. This byte-reader is a separate dependency to validate.
3. Keep source version and observation review distinct. Future approved extraction
   needs typed source locations (page/region/time interval), ship identity,
   measurement kind, units, timezone/clock assumptions and investigator review
   revision. needsReview=false, Verify and a public report are not substitutes.
4. Within the same review transaction, check current permissions, active case,
   original receipt, current source versions and draft/citation equality before
   writing the timeline. Source changes invalidate output, not source evidence.
   Modified may change interpretation but cannot silently substitute evidence.
5. Keep old drafts readable/rejectable under existing access rules. Confirmation
   of unbound evidence-backed drafts requires a NEW explicitly bound draft;
   never retroactively certify the original inference or silently auto-bind it.
6. Package input is historical/untrusted for local admission. Strip or ignore any
   claimed receipt authority and require local revalidation. Do not export a
   transferable live approval token. Define receipt/archive restoration before
   registering a populated new table; preserve closed-world backup failure.
7. Bind source incarnation/version, not just digest: same-content restoration,
   deleted/recreated IDs and change/revert require explicit handling. Current
   append-only custody sequence may help but imported sequences are not local
   authority. A local generation/receipt lifecycle must be defined and tested.

## Acceptance gates before claiming functional delivery
- Forged submit payload and forged imported receipt cannot confer authority.
- Foreign-case IDs, hidden/restricted evidence and revoked permissions reject.
- Current hash follows Change, not original registration SHA.
- Same-SHA replacement/incarnation and change/revert invalidate old receipts.
- Old/imported drafts stay unbound and cannot be silently promoted.
- Signed original and raw bytes never altered by binding or review.
- Byte readers use fd-level checks against symlink/parent replacement races;
  a one-time path check is not sufficient protection.
- Source changed/removed after model/core work yields no saved result.
- Rejected changes only draft review/audit state, not timeline/source; failures
  roll back all attempted state changes.
- New receipt rows do not cause silent archive omission; restore stays historical.
- Local SQLite tests and independent review, then actual API/UI acceptance;
  fake models do not count as real LLM integration.

## Current verification, deliberately limited
service/tests/test_timeline_binding_model_facts.py exercises real temporary
SQLite and existing evidence service: Change leaves registration SHA unchanged
while updating currentSHA; clearing Review after Change remains Unverified;
Access increments viewing count without changing content version/status.
These tests validate design premises only, NOT the proposed binding feature.
Separate independent read-only code review confirmed payload/import and archive
risks. No production source code changed in this design checkpoint.

Independent final model-premise rerun:3/3 passed, zero skips. Reviewer corrected
rejection-state wording; no functional binding implementation was approved.

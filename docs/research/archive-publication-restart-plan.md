# Archive publication and restart: minimal integration design

2026-11-18. **Design only; not implemented, not a recovery guarantee.** Reviewed research parent `31c8b6b3382b45be0e0efcfb86f6c02b4a6d284c`; product comparison `b4df82306d9bab87b938b9e447e27a64b0464406`. No tests, fault injection, HFACS, real files or production configuration were run/read. This supplements archive-member-destinations.md and existing publication/migration research contracts; it does not replace their conservative holds.

## Concrete current order and failure windows

Line references in this section are at the research parent, under service/mcis_service/. PR104 lacks the timeline-origin record call and its rename is at router.py:209 rather than :211; do not confuse the trees.

| Phase | Current code / durable evidence | Failure or interruption interpretation |
|---|---|---|
| Parse and describe | package_intake/router.py:178-181 | No new transaction yet. Parsing may validate HFACS for packages that contain it; a receipt lookup is not necessarily core-free either. No such package was executed here. |
| Allocate staging directory | router.py:182-186 | WRITE_LOCK is process-local. Random staging path and published=False are not a persistent operation identity. Crash can leave an unclassified directory; no ownership inference or automatic deletion is justified by its name. |
| Begin / existing receipt / collision checks | router.py:188-196 | BEGIN IMMEDIATE serializes SQLite writers, not all filesystem writers. A prior receipt can short-circuit; target existence checks alone do not establish exclusive publication across processes. |
| Reconstruct rows and files | router.py:197; package/mcase.py import_case; working_records_archive/service.py restore | DB rows remain in transaction. Files already exist in staging independently of SQL rollback. The mapping report identifies raw/evidence, historical artifacts and DB-only members. |
| Retain source ZIP, receipt, origin and flush | router.py:198-207 | Only source.mcase is explicitly file-flushed/fsynced here. Session flush is not commit. No reviewed code here establishes directory fsync or durable completion for every imported member. |
| Publish final directory | router.py:208-212 | Rename occurs BEFORE session commit. Final directory can exist while DB outcome is pending. published is volatile. A crash between rename and assigning published has no durable recovery label. |
| Commit and return | db.py:67-77; router.py:213 | Session exits through s.commit then returns. Lost response after known commit differs from unknown commit outcome. A thrown error or missing HTTP response alone cannot prove rollback. |
| Exception/final cleanup | router.py:214-218; db.py:72-77 | Current code removes target if published and always removes staging; db session attempts rollback on Exception. This is code ordering, NOT proof of a reproduced production loss or of cleanup safety under an ambiguous commit. Cleanup itself may fail. No changes made here. |

Existing IntakeReceipt is real and must be retained: router.py:93-136 checks case, source ZIP length/digest, reparses the ZIP and applies existing access checks. It does **not** prove that every restored raw/evidence/history artifact still matches, or that all derived DB state is complete. Historical import receipts are separately non-active. Neither kind is a general readiness token.

## Chosen minimum direction (proposal, deliberately different order)

Prefer **commit held DB state before publication**, reusing the research waiting_publication idea. Do not simply move rename in the current router: that would expose a case without files until universal readiness gates exist. The following is one proposed protocol, not a new implementation or authorization:

1. Before adoption, establish externally retained database identity, migration version and selective gates on every case entry. Existing legitimate cases keep their current policy path; protocol-enabled unknown cases stay unknown. Identity/migration ownership remains unresolved.
2. Create a durable operation claim bound to database identity, case ID, original package digest, layout version and owned staging/final locations. Acknowledgement only after confirmed claim commit; an uncertain claim outcome is inspection-only. Do not backfill historical directory ownership.
3. Prepare the complete staged inventory under that claim. Persist exact member paths/sizes/digests, including history artifacts from the mapping, and a manifest digest bound to the operation. This requires an established single-writer/closed-writer and durability contract; a filesystem scan alone does not establish either. No source authenticity claim.
4. In ONE DB transaction reconstruct case/history, preserve inactive receipts, append import audit, link the existing intake receipt to the operation, and mark waiting_publication with the same manifest digest. If commit acknowledgement is lost, do not reconstruct again. Inspect fresh DB state by exact operation ID.
5. Only a confirmed held commit plus a verified owned staged inventory may enter a separately authorized no-replace publication step. Define same-filesystem rename/durability guarantees for the deployment first. This document does not authorize retry, deletion, copying over targets or ready promotion.
6. After publication, compare operation identity and exact destination inventory to the committed manifest. Only after writer exclusion, durability and all entry gates are independently demonstrated could a later atomic DB transaction record ready. Until then even matching observations return held/not-ready. An HTTP success receipt would require that final transaction to be confirmed; otherwise result is pending/unknown.

## Read-only restart decision table

These are conservative proposed classifications, not automatic repair instructions. Inspect DB in a read transaction and retain filesystem observation uncertainty. Current observer is not a synchronized DB/filesystem snapshot.

| Observations | Classification and permitted consequence |
|---|---|
| External identity unavailable/mismatched, schema incomplete, unbound directory, or claim conflicts | unknown; no success, replay, delete, publish or ordinary-case adoption |
| Confirmed claim only, no attempt recorded | prepared/claimed observation only; no inferred retry permission |
| Attempt recorded, no matching committed business marker | unknown outcome; absence of marker alone is not proof of rollback; retain files |
| Matching held DB commit and matching staging, final absent | publication pending; remain unavailable; read-only inspector does not publish |
| Matching held DB commit and matching final directory, staging absent | publication observed, not ready; do not infer writer closure or fsync guarantees |
| Both staging and final present | ambiguous ownership/publication; hold, retain both; do not choose by timestamp |
| Committed rows but missing/incomplete/unexpected files | hold/inconsistent; no partial success, no reconstruction from guessed bytes |
| Final directory present without matching committed marker | unknown/orphan observation; do not delete or adopt, even if package digest matches |
| Ready marker present but publication binding/identity differs without a validated subsequent business revision | unknown, not success; escalation under established policy, no silent repair. Legitimate later changes are classified separately below. |
| Response lost after verified final ready commit | proposed receipt reconciliation could return the recorded result under unchanged authorization, not execute the import again; not supported by current research ready capability |

## Reuse, gaps and implementation gates

Reuse: existing IntakeReceipt and source.mcase, archived inactive import records, exact-member validation and lineage, research operation/commit markers, migration classification and normal-case registration. Do not create a second independent success ledger.

Research publication_observer.py covers raw/evidence plus original ZIP and a fixture marker; it lacks historical artifact mapping and cannot establish concurrent writer exclusion. migration_protocol.py/reopen observes DB and publication separately. readiness_gate.py wrappers are research-only, with no ready promotion. No component currently proves this complete proposal.

Before product work: enumerate list, case reads/writes, export, body/digest-derived receipt lookup, direct evidence/download and analysis paths; bind every applicable operation to one readiness decision WITHOUT weakening existing permissions. Preserve normal legacy cases and newly registered normal cases. Specify a fail-closed migration that does not mistake missing metadata for legacy. Do not enable unsupported media/conflict formats as part of this protocol.

Unresolved prerequisites: trusted external identity source and lifecycle; all writers/descendants and closed-write evidence; filesystem rename/no-replace/fsync semantics; durable distinction of unknown versus committed outcomes; operation-to-receipt migration; full entrypoint gate coverage; resource bounds; supported old archive behavior. No claim of production crash recovery, SSO, permission equivalence or global filesystem immutability.

Next bounded work after design review: extend the isolated expected-layout contract to include declared historical artifact members and bind its canonical digest to the existing operation marker. Validate with ordinary synthetic supported 1.2 packages and explicitly reviewed nodes only. This improves comparison coverage, not publication readiness. Do not run paused/security/write-refusal probes or actual crash injection under this task.

## Review performed

Read-only source comparison, mapping review and document diff/whitespace check only. No runtime tests or recovery executed. All statements about failure windows are static inferences, not reproduced failures. Only this document is delivered; no credentials, databases, media or private case material. Production protections and existing restoration logic unchanged; no merge/deploy.


## Review clarification: publication baseline versus a living case

Added after independent static review of parent `3b273bee4ba486f1100a91c08a53e0257d530957`. Still design only. The first-publication manifest describes an immutable **historical baseline**, not an eternal expected image of the entire case directory/database. Preserve that manifest and its operation/commit binding; never rewrite it to make later bytes appear originally published.

Normal business can change the case: `case_metadata/router.py:update_metadata` writes CaseRow and an audit event; `working_records_archive/router.py:content` even appends a custody Access event during an authorized read. Evidence intake adds files/rows; subsequent package export can retain another original-package artifact. Consequently, ready must not require all current rows/files to remain equal to the first-publication snapshot. Conversely, a change cannot be accepted merely because it occurred after ready. Distinguish immutable historical members, mutable/current records, and append-only history with explicit existing version/audit linkage. The complete classification of file writers and a trustworthy current revision/checkpoint protocol are unresolved; do not enable the proposed ready state until this is specified. No present audit entry alone is asserted to prove file authenticity.

### Ownership must span the handoff

A single-writer claim must cover staging, final-byte verification, the ready transaction, AND transfer to ordinary entrypoints. Releasing ownership between verification and ready leaves a race; releasing after ready but before normal writers inherit the same exclusion discipline also leaves a race. A proposed durable generation/fencing token must bind operation, database and storage identity; every writer must check it or be otherwise excluded. The mechanism, lease/owner-death rules and storage durability are not implemented or selected here. A PID, age, process-local WRITE_LOCK or fixture marker is insufficient proof. An old owner must not resume after ownership changes. Multiple service processes and worker descendants must be included before calling this exclusive.

### Additional state distinctions

| State/evidence | Classification / constraint |
|---|---|
| Claim commit unconfirmed | unknown claim; inspect exact identity, do not create a replacement claim or retry |
| Confirmed claim, preparation incomplete | preparing/held; partial files are not a completed inventory; no success or automatic cleanup |
| Prepared manifest exists, writer closure or durable preparation not proven | prepared-unverified/held, even if hashes currently match |
| DB held commit confirmed, publication pending | pending publication, not business-ready; any future continuation must satisfy all conditions below |
| Final verification complete but ready commit unconfirmed | ready outcome unknown; read-only reconciliation only, no import or publication replay |
| Ready commit confirmed, no later business revisions | initial publication baseline may be compared under ownership; ready does not replace authorization |
| Ready followed by linked, authorized business changes | active modified case; retain baseline, inspect current version/history separately; do not classify expected changes as failed initial publication |
| Claimed later change lacks required version/history binding | unknown current consistency; no assumption that ready makes it legitimate |
| Competing owner, stale fencing generation or conflicting operation for same case | ownership conflict/hold; timestamps do not choose a winner; no overwrite or automatic takeover |
| Genuine old normal DB with explicit migration inventory/identity | retain established normal policy path; do not invent historical ready evidence |
| Restored/copied old DB missing or conflicting external identity or migration state | unknown migration/recovery provenance; neither new claim adoption nor automatic legacy fallback. Backup of DB and external identity must itself have a defined recovery contract |

### Three separate gates; no implicit permission to resume

1. **Business authorization**: existing actor/case/source permissions still apply at the time of every action. A protocol marker or operator approval does not grant these permissions. Production trusted identity remains unresolved.
2. **Protocol preconditions**: matching operation/source/manifest/database identities, unambiguous commit observation, exclusive current ownership, supported layout and all-entry gating. Passing authorization does not establish these facts.
3. **Operational approval**: any future recovery mutation needs an explicit, auditable operational procedure and authorized approval for that exact operation/action. Manual approval cannot waive unknown commit, missing bytes, ownership or business authorization. Current task authorizes documentation only.

Current implementation has NO supported interrupted-publication continuation API: `commit_observer.py:restore_once` permits only an unattempted claim; subsequent attempts are inspect-only, and readiness wrappers never promote ready. Thus all interrupted operations remain read-only/held today.

A future narrowly bounded continuation could be considered only for a confirmed held DB transaction and a fully bound prepared inventory, with target-state evidence, exclusive fenced ownership, current authorization and explicit approval. It would complete the missing publication/ready transition, not reconstruct business rows or reactivate historical receipts. Unknown commit, conflicting paths/owners, missing immutable bytes or incomplete history prohibit continuation. Returning a recorded result after a proven commit is reconciliation, not re-execution. The persistence of continuation intent/result, allowable idempotent substeps and crash boundaries need a separately reviewed contract before implementation; no automatic retry/delete is proposed.

No runtime tests or fault injection accompanied these clarifications. No change to product logic, migration, permissions or archive protection.

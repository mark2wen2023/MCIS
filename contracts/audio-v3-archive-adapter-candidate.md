# Internal audio-v3 archive component adapter — isolated candidate

Base bce6f5bd7c0563d7434ed56ad074a0cdfe49e78e. No HTTP route/default-app wiring, ZIP/download, restore, active receipt registration, task execution or permission-policy changes.

## Call and authorization boundary

`audio_review.archive_candidate.build_candidate(ctx, session, case_id)` accepts the existing context and session. Caller must have flushed ordinary setup changes and acquired the existing reserved SQLite writer through `reports.access.begin`; proof must refer to the same active SQLAlchemy transaction, connection and thread. Candidate does not open another database connection, commit, roll back, acquire a conflicting process lock, or write an audit. Caller remains responsible for its existing outer transaction/lock lifecycle and must discard output if that transaction fails. This is not an uncertain-commit resolver.

Before returning any native inventory/raw audit, reuse BOTH evidence-intake authorize and full working-archive access checks. Existing full-content policy is more restrictive than ordinary note editing; no claim that every audio editor can extract all audit history. Real identity is still the application's existing self-reported role context, not authenticated SSO. This candidate grants no export permission.

## Bounded extraction

Use the same transaction's native SQLite connection for complete case-scoped inventory and unique media revision/audit matching. Accept local successful audio tasks with original captured v3 revision0 only. Imported v2/v3 review runs, pending/failed/unknown tasks, image records and other business-state tables outside the narrow component scope reject. Base case/vessel/track/environment/evidence/custody/audit/policy rows remain verbatim in `nativeInventory`; they are NOT declared a complete restorable case package.

Every unique audioReceipt is resolved once through the existing load_receipt(ctx, same_session, case, digest). That function enforces existing source authorization and registered-byte checks. Cache the returned immutable byte value and receipt; reuse those bytes for PCM/timebase checks, hashes and member assembly. No second path read for sealing/packaging. Require every case EvidenceRow to be represented by these source registrations; extra evidence rejects rather than disappears. Preserve receipts as inactive documents only.

Retain every run's full initial document, every human revision, task raw result, native machine artifact, recognizer metadata, full task document and whole original audit lines. Build the existing proposed member index from native records, not hand-authored test indexes; enforce unique audit links and both member and audio-v3 byte consistency. Raw/task serialization uses the existing canonical JSON representation. Captured-from-initial means revision0..N exist; it does not invent history preceding revision0. Recorded task succeeded is retained, not re-executed or newly attested.

Output contains `index`, `payloads`, `nativeInventory`, and consistency results. Always export_allowed=false, restore_ready=false and task_execution_allowed=false, scope=internal-audio-v3-component-not-a-complete-case-package. Any mismatch/missing/unsupported source refuses the call, without a partial result. Existing native HTTP exceptions remain existing policy/integrity outcomes; internal consistency failures are ValueError. There is no new public error mapping.

## Remaining boundaries

This reuses the current original-file reader; it does not independently certify path safety, prevent external filesystem mutation, or prove a simultaneous filesystem snapshot. No earlier restricted tests were repeated. SHA equality is supplied/registered byte consistency, not authenticity. Long writer lock and memory costs (inventory plus duplicate artifact members) remain unbenchmarked. Member bounds remain16MiB each/64MiB total, plus the separate bounded native inventory; do not claim a process-wide memory budget.

The adapter does not read or classify audio-asr-jobs working directories, create a complete case ZIP, invoke product parser/restore, repair missing histories, reactivate receipts, or handle publication/crash recovery. Extra operational files and whole-case completeness still need the existing closed-world exporter checks and further integration. No archival allowlist is widened. The authoritative product export still refuses media records.

# Atomic normal-case registration — isolated developer candidate

Parent cab1da38552dedf0d905ce6fc843bea7ae308c2c. Branch research/restore-normal-case-registration. No production module/route/permission change, product restore remains disabled. No PR104/body update, restricted operation retry, deployment or merge.

Reviewed actual POST/cases: validates existing case schema, permits LeadInvestigator/Investigator role names, writes CaseRow and case.create audit in session context. The isolated creator mirrors those validation/role semantics but is NOT the HTTP endpoint and does NOT authenticate operator/role. It reuses actual put_doc and audit.append, with WRITE_LOCK then BEGIN IMMEDIATE held through commit.

Implemented a separate optional offline_normal_case_registration table: case ID, expected database identity and case.create audit sequence. Three writes (case, audit, registration) share the same transaction. No migration-time legacy inventory backfill. Existing case/audit/legacy record or operation/commit/readiness binding for the ID refuses creation. No adoption endpoint, no blind retry, no automatic compensation.

Classification recognizes a new registration only with matching database identity, exactly one CaseRow and matching create audit event/sequence/entity. Restore ledger state still takes precedence. The old enum string legacy_policy_required means continue existing policy, NOT a claim the new case existed before migration. Optional table absent/missing binding keeps unknown new cases unknown. Original ledger-only readers safely remain conservative. This is association validation, not full audit-chain or file authenticity proof.

Command from service/:
```
PYTHONPATH=.. /workspace/mcis/service/.venv/bin/pytest -q tests/test_restore_normal_registration.py tests/test_restore_classified_entries.py tests/test_restore_migration_protocol.py tests/test_conflict_readiness_gate.py tests/test_conflict_commit_observer.py tests/test_conflict_publication_observer.py
```
Final64 passed in29.00s:11 new ordinary synthetic cases plus53 existing, not additive with prior runs. Coverage: successful real temporary-SQLite writes/read classification; rejection of duplicate/adoption and claimed case; wrong database identity; exception after case/audit/registration rolls back all three; two thread-barrier-synchronized sessions same ID yield one success and one conflict; missing/wrong registration binding stays unknown; fresh-process reopening recognizes committed association. No HTTP/production identity tests or previously restricted security/ECFC operations.

Initial7 tests failed because synthetic coordinates used lat/lon instead of existing required latDeg/lonDeg. Corrected fixture ONLY, kept schema validator unchanged; then7 passed0.79s before adding four more cases and running final64. Faults are explicit exceptions, not actual process crashes or uncertain SQLite commit. Concurrency is two local threads/sessions, not multiprocess production load.

Not implemented: production ordinary-case registration wiring/migration, durable externally protected identity, universal access gate, full ledger consistency, file publication or ready promotion. The store creates and owns its temporary database; it does not accept a production DB path. Exceptions during genuine uncertain commit must be treated as unknown externally; this API does not implement a recovery/idempotency receipt for that condition. No files/originals/models involved. Existing unknown rows remain unknown. Readiness still false for restored cases.

Freeze RESTORENORMALREGISTRATION supersedes prior migration_protocol.py/contract pins. Parent frozen files otherwise unchanged; no claim all historical manifests match. Candidate unpushed and not independently accepted at recording time.

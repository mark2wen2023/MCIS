# Existing protocol inventory and durable commit observation

Base660874008c44dd313b0a66e971ad78c3a1f14589. Existing product IntakeReceipt DOES
persist successful import metadata. Earlier planning's missing operation/commit state
must not be read as absence of all persistent receipts. No protected receipt lookup
or restricted tests executed: inventory below is static source reading.

| Entry | Existing behavior / missing readiness dimension |
| --- | --- |
| GET /api/v1/cases | cases/router->service.list_cases selects rows; no pending publication state |
| GET /cases/{id}, /overview | service.load_case checks existence; normal metadata cases remain valid |
| timeline/other case handlers | generally load_case plus existing category policy, no restore-operation gate |
| reports case_info/check_access | existing full-content/report checks and special public-case handling; no publication protocol |
| GET /cases/{id}/export | role gate, WRITE_LOCK, SQLite IMMEDIATE, mcase.export_case direct CaseRow plus existing complete-source guards |
| POST /packages/intakes:preview | existing parsed format/policy/case collision checks |
| GET /packages/intakes/{digest} | existing receipt() authorizes target case, checks CaseRow, retained source ZIP length/hash/format, source access for supported extensions; archived-only receipt refuses |
| POST /packages/intakes:commit | same persistent IntakeReceipt lookup; stages source ZIP, inserts receipt/origin, renames, then DB commit; no operation-state recovery protocol |
| create_app startup | schema/optional seed and routes; no pending publication reconciliation |

New research commit_observer.py uses the SAME owned SQLite as actual restored rows,
not a second mock ledger. UUID claim/attempt is durable first; commit marker inserted
in existing restoration transaction after full reconstruction verification. Independent
research metadata only, active source receipt table empty. Directory remains after
context exit and failure; no auto-delete/finalizer. No product file is published.

Fresh subprocess uses mode=ro SQLite to inspect markers/source BLOB identity. All
statuses are non-ready/non-retry/non-delete; even observed commit remains publication
unverified. It cannot verify current business integrity or prove production readiness.
No changes to production modules or case listing, so normal existing cases are not
newly hidden/gated. Their future selective readiness integration remains unimplemented.

Command from service/:

    PYTHONPATH=.. .venv/bin/pytest -q tests/test_conflict_commit_observer.py tests/test_conflict_v2_sqlite_continuation.py tests/test_conflict_archive_envelope_v2.py tests/test_conflict_archive_receipts_v2.py tests/test_conflict_restore_current_compatibility.py

Targeted6passed5.62s: durable normal commit, fresh-process read, lost-response exception
after actual commit, journal/before_commit rollback markers absent, duplicate attempt
refusal, missing DB not created, source/operation mismatch. Tests compare DB counts
before/after inspection and retries. Retained synthetic temporary directories are
intentionally not automatically deleted by this implementation/test; no DB is staged
in Git. Expanded final result recorded in REQUESTS.md.

Limitations: no actual crash/power loss/SQLite uncertain commit simulation; the response
loss hook runs after commit returns. No staging/publication/owned-object manifest or
product-ready marker, no active import receipt/lineage migration. No application-wide
readiness/permission equivalence claim, real identity, browser, production case or
original read. Product experimental imports stay rejected. No restricted security/
ECFC operation, merge or deploy. Read-only observation is a limited necessary slice,
not a completed recoverable product import.

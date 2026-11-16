# Empty case list / orphan ledger — developer candidate

Parent c60f857db046cdaada06d0ecc31826c3996175a1, isolated research branch research/restore-empty-ledger-consistency. Production app and permissions unchanged; restore_ready=false and product import/export protections unchanged.

Before correction, two new ordinary synthetic cases failed: an empty cases table with a lone commit or readiness row (no claim) was classified unknown for that ID, but list_cases returned[]. Both failed DID NOT RAISE ReadinessUnknown in1.11s. Cause: empty-list fallback validated protocol identity/columns with LIMIT0, never existing row associations.

Minimal runtime delta: seven lines in research readiness_gate. Empty listings with expected identity now inspect distinct case IDs from operation/commit/readiness tables via the same classification. Unknown binding raises ReadinessUnknown. Explicitly run validation when identity is supplied even if an empty-ID claim collides with the initial sentinel. No row/marker deletion, compensation or retry.

Five added parameterized cases: orphan commit and orphan pending, each with/without an empty-ID claim; consistent unattempted claim remains held and yields no visible cases. Existing normal-empty, old-case compatibility and malformed-schema regressions remain. Empty output with consistent held claims means no visible cases, not proof that no pending operations exist.

Final command from service/:
```
PYTHONPATH=.. /workspace/mcis/service/.venv/bin/pytest -q tests/test_restore_classified_entries.py tests/test_restore_migration_protocol.py tests/test_conflict_readiness_gate.py tests/test_conflict_commit_observer.py tests/test_conflict_publication_observer.py
```
50 passed in27.84s, developer synthetic tests only (45 existing+5 added). Intermediate48 passed40.59s before sentinel follow-up, not the final result; counts overlap and are not additive. No restricted security/ECFC test, private original, real crash/uncertain SQLite commit, browser, production identity or model executed.

Scope remains research empty-list consistency, not a universal ledger integrity audit or production readiness. Direct product services are not intercepted; external identity retention, ordinary new-case registration, all gates and durable publication still pending. Prior freeze entries for readiness_gate/contract/entry-test are superseded by RESTOREEMPTYLEDGER; no claim all old pins match. No push, PR104 edit, PR-body retry, merge or deployment this turn.

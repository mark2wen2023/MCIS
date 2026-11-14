# Independent review — policy PUT initial lock failure semantics

2026-11-14. Isolated /workspace/mcis-policy-lock, base72269e3.
Reviewer changed only tests_acceptance/policy-write-busy and this report. No product edits,
commits, remote writes, merges or deployment. Reviewed AGENTS rules and candidate contract.

## Actual execution

From service/:

```sh
.venv/bin/python -m pytest -q --import-mode=importlib \
 ../tests_acceptance/policy-write-busy/test_independent.py tests/test_policy_write_busy.py
```

**16 passed in3.64s**, comprising4 independently authored cases and12 implementation cases.
Output: tests_acceptance/policy-write-busy/results.txt. No skipped cases.

```sh
.venv/bin/python -m pytest -q tests/test_recorded_digest_delivery.py \
 tests/test_intake_authorization_transaction.py
```

**35 passed in7.33s**, no skipped cases. Output: protection-regression.txt in same directory.
These are reruns of existing digest/authorization tests, not newly independent test design.
Product SHA snapshot is product-hashes.txt; no source changes were made by reviewer.

## Independent evidence

1. A real separate SQLite connection holds BEGIN IMMEDIATE. Policy PUT uses test-only60ms
   busy_timeout and returns503 with exact not_committed/retryable detail. SQLAlchemy SQL
   capture records only BEGIN IMMEDIATE for the failing request: no case/policy read or
   policy/audit write occurred. Stored policy and audit count remain unchanged.
2. Another thread owns the real application WRITE_LOCK throughout a successful policy PUT.
   Request completes200 within2s without waiting for that lock. At audit append, real
   transaction/connection/thread reservation proof is checked; another SQLite connection
   cannot acquire writer (actual SQLITE_BUSY). One policy update and one audit persist.
   This confirms the inherited proven-reservation audit path prevents lock inversion.
3. An explicitly injected SQLAlchemy after_commit event raises numeric SQLITE_BUSY AFTER
   actual transaction commit. Response stays500, has no retryable/not_committed assurance;
   subsequent database read proves changed policy plus one audit persisted. A failed
   response cannot be treated as proof that the write did not commit.
4. Under actual initial writer contention, simulated Session.rollback failures persist
   through cleanup. Response is500 without not_committed/retryable. Actual unchanged
   policy/audit does not justify falsely promising rollback success to the caller.

These are synthetic local databases and controlled faults; no remote or production
identity/authorization assumption is made. The two injected failure tests are explicitly
simulations; contention and the post-commit database state are real SQLite behavior.

Implementation tests additionally exercise transient release then success, manual re-read
and retry, numeric extended BUSY/LOCKED recognition, invalidated connections, text-only and
other-code rejection, body failure, and commit-before/after fault classification.

## Assessment

No blocking issue found within the limited initial-reservation contract.503 assurance is
restricted to recognized numeric SQLite BUSY/LOCKED at initial begin, non-invalidated
connection, and successful rollback before any policy/audit writes. Later errors escape;
there is no automatic retry and generic500 remains outcome-unknown. Role/schema checks
stay first. No digest check, writer reservation or revocation guard is weakened by the
candidate;35 affected regression cases pass.

This does not certify all database faults, full-system behavior, other dialects, HTTP
transport delivery guarantees or production policy identity. Default production busy
wait is not shortened (tests override only their connections). Throughput, fairness,
large-file lock hold times, cancellation and operational retry UX remain unmeasured.
A client must reread current policy before a deliberate retry and must not blind-retry
an unknown500. Complete policy replacement can otherwise overwrite concurrent changes.
No merge/deployment or overall attachment-integration approval is implied.

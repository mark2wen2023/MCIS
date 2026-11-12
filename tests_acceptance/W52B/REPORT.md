# W5.2b independent acceptance

Result: **54 independent synthetic tests passed** (40 API/DB + 14 writer-proof/concurrency tests), plus a real-browser lifecycle against the actual FastAPI service and fresh synthetic database. All **24 final frozen file hashes matched**. The original lock-order red test also passed unchanged in a separate targeted rerun; it is overlapping coverage, not an additional unique test. The bounded lock-order defect below is resolved within the tested scope. No implementation files were edited by acceptance.

## Verified

- Empty unsigned creation, exact Unicode/whitespace-preserving question/answer append, reopening, immutable metadata receipts, read-only recovery and no duplicate mutation on replay.
- Concurrent identical requests produce one first success and one replay; different request IDs at the same document version produce one success and one conflict.
- A legacy writer changes the complete-document digest; replay returns its historical receipt alongside the current digest, while a new stale append fails.
- Same request ID with changed body, optional-default presence or operator conflicts. Receipt access isolates actor and case. Current read permission can recover, but current write permission is required for POST replay. Signed records allow historical metadata replay but reject new append.
- Policy revocation, changed or deleted registered source blocks current access and replay. A paused append holds its SQLite reservation until commit; subsequent revocation commits and recovery denies. Legacy unbound hashes remain visibly unverified and cannot be appended through the new route.
- Injected document, audit, receipt-insert and final-commit failures leave all database tables unchanged; retrying the same request succeeds after removing the fault. Receipt UPDATE/DELETE is rejected. Deleted records do not release their IDs for reuse.
- Orphan receipts still block whole-case package export. Recovery does not fabricate a current record when it has disappeared. Missing-request lookup is read-only and returns the uncertainty-specific error.
- Strict acknowledgement/type/unknown-field/time/digest checks; 16,000 Unicode-codepoint boundary, 256-round cap, fragment limits/substrings, duplicate JSON keys, invalid UTF-8, unpaired surrogate, nonfinite values and oversized bodies.

## Real browser

The browser used the actual service, not API doubles. It checked the prominent whole-case backup warning and required checkbox; created an empty record; appended original text; allowed the actual append to commit and then deliberately dropped its HTTP response; reloaded, recovered through a read-only receipt GET and reopened the current record. Exactly one appended turn remained, preserving its text. A separate actual legacy POST then caused a real stale-version 409: the editor retained the unsaved answer and disabled stale resubmission. Actual package export returned the unsupported-receipts 409. Reload reopened both committed turns.

There were no browser page errors. This independent browser scenario does not claim exhaustive identity/case-switch or delayed-response UI coverage; those are not counted as independently exercised here.

## Corrections during test development

The first expanded API run was 37 passed / 1 failed because the test referred to a nonexistent evidence table name. The fixture cleanup was changed to use the evidence ORM model; its safety assertions were retained. The first browser attempt asserted before its intercepted real HTTP request completed. Waiting explicitly for that completion corrected the harness race. Original local logs were retained, not published. Neither event required a product change.

## Boundaries

Synthetic data only, `seed_demo=False`. No external model, professional core, W11, real investigation report, deployment or publication was exercised. These are local self-reported role/operator checks, not authentication or legal signature. Successful persistence does not establish factual accuracy. `.mcase` backup remains deliberately unavailable for a case with manual-entry receipts; this is not archive support. Read transactions reserve SQLite's writer and do not retract already-delivered bytes. Tests are targeted, not a full-repository acceptance claim.

## Reproduce

From repository root:

```sh
PYTHONPATH=service service/.venv/bin/pytest -q tests_acceptance/W52B/test_manual.py tests_acceptance/W52B/test_locks.py
MCIS_BROWSER_BIN=/path/to/existing/chromium python tests_acceptance/W52B/browser_real.py
sha256sum -c tests_acceptance/W52B/verified-impl-sha256.txt
```

Browser needs system Python Playwright, existing Chromium, service dependencies and installed web dependencies. Both temporary servers bind only to loopback and use a temporary database. No installation is performed.

## Lock-order finding and final disposition

The original real two-request interleaving paused manual creation after acquiring SQLite's writer reservation but before audit insertion. Package export acquired the process write lock and then tried to obtain the database reservation. The manual request next needed the process lock. After approximately 5.11 seconds, export returned sanitized `500 INTERNAL_ERROR` with `no-store`, and creation completed with 201. This demonstrated a finite timeout / recoverability defect, not data loss, disclosure or an infinite deadlock. Its original red result is retained locally.

The implementation now recognizes only a successful explicit `BEGIN IMMEDIATE` reservation bound to the same active root transaction, connection and thread object, with a live physical SQLite transaction. Audit append can then rely on the database writer reservation instead of acquiring the inverted process lock. Actual final code was independently inspected.

Fourteen independent regressions passed:
- Eight fallback probes: fresh session, ordinary BEGIN, committed/rolled-back proof, unproved nested transaction, reused connection/session proof, foreign thread and non-SQLite dialect branch. Lock-entry traps verify these do not silently take the exemption. The non-SQLite probe exercises branching, **not an actual non-SQLite database**. The foreign-thread probe uses a quiescent session sequentially only, not concurrent Session use.
- A proved writer bypasses the process lock; rollback removes its audit mutation and a new root transaction must receive new proof.
- Proved outer writer with savepoint: rollback-to removes its audit entry; release and a later append maintain contiguous sequence and hash chain. Unproved savepoints retain fallback behavior.
- Manual and legacy interview writer first versus actual export: both complete without the former busy timeout; export sees the committed receipt and returns 409.
- Export first: returns a valid prewrite package with no later transcript or manual-create audit, then the manual write commits. Subsequent export returns 409. A legal earlier snapshot is not treated as a dirty export.
- Two actual independent Python processes share one SQLite database and append 25 reserved-writer audit entries each. All 50 sequence numbers are contiguous and each previous hash matches the preceding raw line.

Final disposition: **D1 resolved for this scoped implementation; W5.2b accepted within the stated boundaries.** The 54-test rerun, unchanged original red-test rerun, real-browser rerun and 24-file checksum verification all passed after final refreeze. This does not certify unproved legacy transactions, all routes, non-SQLite operation, cross-thread Session usage, or whole-system multiworker support. Raw driver-level transaction manipulation is not a supported proof-lifecycle path. Existing database-wide contention and already-delivered-byte limitations remain.

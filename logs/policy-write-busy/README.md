# Policy initial writer contention — isolated safety candidate

2026-11-14. Base72269e39fccb3d85b12734c52c9bef93a78040c6. Review branch
codex/policy-write-busy-review, directly based on72269e3. Publication for cross-environment
review is explicitly authorized. No merge/deployment; main and prior review refs unchanged.
Only two product files: new redaction/write_access.py and two lines in policy PUT router.
No general/global database exception handler, automatic retry, reduced timeout or shortened
protected evidence transaction is introduced.

## Outcome semantics

PUT access-policy first validates role/schema, then reserves the SQLite writer with existing
reports.access.begin before case/policy reads or policy/audit writes. Only an OperationalError
with an actual sqlite3.OperationalError and numeric BUSY/LOCKED base/extended code, on a
non-invalidated SQLite connection during that initial reservation, is eligible. Successful
session.rollback() must complete. Only then503 POLICY_WRITE_BUSY states:

```
{"detail":{"commitState":"not_committed","retryable":true}}
```

Message explicitly requires rereading current policy before a deliberate retry. No code
replays the mutation. Whole-policy replacement is not versioned and blind stale retry could
overwrite concurrent changes. Retryable here means known uncommitted, not automatic replay.

Body/flush/commit-phase errors are outside this classification, even when their numeric
code says BUSY. Missing codes, message-only 'database is locked', other codes/dialects,
invalidated connection, failed rollback are not eligible. Existing500 INTERNAL_ERROR does
not state transaction outcome; it MUST be treated as unknown, not proof of no commit.
There is no UI outcome-state redesign in this backend candidate. Existing web api.ts uses
one fetch with no retry loop (static inspection only, no browser claim).

Tests actually commit SQLite then inject Session.commit or SQLAlchemy after_commit BUSY.
Response remains500 WITHOUT not_committed/retryable; policy and audit really persisted.
Conversely a precommit failure leaves no writes but still conservatively reports unknown.
Rollback-failure tests simulate failures; no not_committed promise is issued.

Reservation sets the existing real transaction/connection/thread proof used by audit.append.
Independent test holds global WRITE_LOCK from another thread, verifies actual SQLite reserved
writer plus a second connection BUSY, and proves policy update does not invert lock order.
Evidence reads/hash verification/authorization ordering remain unchanged.

## Executed tests (overlapping, do not sum)

| Set | Actual outcome |
|---|---|
| Implementation busy12 plus existing digest29 |41 passed/6.71s (focused.txt)|
| Independent4 plus busy12 |16 passed/3.64s (acceptance results)|
| Independent rerun existing digest29 and intake authorization6 |35 passed/7.33s|
| Actual slow-read/API contention and mismatch rollback |6 passed,17 deselected/17.86s|
| Broader selected affected suites |247 passed,4 failed,1 skipped/65.54s|
| Unchanged72269e3 legacy interview/access baseline |35 passed,4 identical failures/17.03s|

Read-contention tests use actual8MiB files and per1MiB artificial read delay (explicitly
simulated storage latency), real TestClient endpoints and real independent SQLite connections.
Default app busy_timeout remains5000ms for these tests:
- During800ms/chunk slow GET/export, policy PUT returns503 after5.060/5.020s, no policy update
  audit, original ReadWrite permission remains, subsequent content GET200. This revocation
  did NOT commit; no response claims it did.
- With50ms/chunk, policy PUT waits0.503/0.549s then200, exactly one policy audit, subsequent
  content GET403. Ordering is authorized read first, committed revocation second.
- Digest-mismatching primary read409 rolls back, waiting SQL revocation commits afterward,
  next content GET403. No integrity or revocation protection was traded for performance.
The17 deselected measurement scenarios were NOT rerun for this candidate; prior study
results are separate. Source is tests/test_policy_lock_read_integration.py; output and
raw measurements are read-contention.txt and read-contention.jsonl.

Implementation/independent short-timeout tests explicitly use test-only100ms/60ms connections.
They do not change application defaults. Failure injections are labeled simulations; successful
commit and subsequent persisted-state checks still use real SQLite.

Broader command from service:
```
.venv/bin/python -m pytest -q -rs tests/test_policy_write_busy.py tests/test_recorded_digest_delivery.py tests/test_legacy_safe_delivery.py tests/test_interviews_redaction.py tests/test_access_workbench.py tests/test_evidence_intake_w42.py tests/test_intake_authorization_transaction.py tests/test_report_output.py tests/test_contracts.py
```
Four failures are old test_interviews_redaction cases: interview_list_summary,
redaction_by_role, crosscheck_requires_confirmation, statement_add_and_review. Exact same
failures on unmodified72269e3 in legacy-baseline.txt; no assertions removed or softened.
One skip: test_evidence_intake_w42 requires existing .NET SDK. No HFACS suite was run here;
previous HFACS failures are not claimed fixed. No browser/full-system/production acceptance.

Independent report: DEFECTS/policy-write-busy.md;
acceptance evidence: tests_acceptance/policy-write-busy/.
Hashes: logs/policy-write-busy-impl-hashes-frozen.txt. Product changes unchanged after review.

## Limits and next review

This handles only initial reservation of policy PUT. Other endpoints' lock errors and
later policy-write failures still use their existing error behavior. Generic500/network
failure must be reconciled against current policy/audit, never blindly retried. A transport
failure can lose even a successful response; no idempotency/receipt protocol is added.
Reservation still spans full evidence reads; global lock waits, starvation/fairness,
cancellation, memory growth and long-read throughput are not solved. No new performance
claim. Earlier measured long-read costs remain. Main/prior review refs unchanged; candidate awaits
coordinator review and does not grant integration/deployment approval.

Test artifact portability: the slow-read test now records JSON only when
MCIS_POLICY_LOCK_RESULTS is explicitly set, with no hard-coded required output directory.
Reran the same six selected cases after this test-only change; see read-contention-portable.txt
and read-contention-portable.jsonl. Product code/hashes were unchanged. Reproduce from service:

```
MCIS_POLICY_LOCK_RESULTS=/tmp/policy-contention.jsonl .venv/bin/python -m pytest -q tests/test_policy_lock_read_integration.py -k 'api_revoke or sql_revoke_after_mismatch'
```

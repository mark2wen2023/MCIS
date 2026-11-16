# Isolated v2 new-meeting ledger

Parent: 8733419e654df24b030befc86e45f9487748db03.

## Implemented

NewMeetingLedger creates only a new exclusive file and v2 schema. Meta binds a
new ledger UUID, meeting UUID and pinned packet. Initial state is a deterministic
revision-zero genesis; later actions each have a caller-supplied UUID operation ID.
Current state, operation input digest/result and sequenced audit event with before/
after state digests are saved in one BEGIN IMMEDIATE transaction before returning.
Synchronous FULL is retained. Operations are capped at 128 in this research API.

The existing pure reducer supplies stable four-role/two-round tickets, request
IDs and 2/16 limits. v2 additionally records explicit operator stop, keeping prior
completed declarations and marking active/pending as incomplete_stopped/unknown.
State is one versioned JSON projection; audit replay must exactly reproduce it.
No v1 RequestBudget writer is reused or changed. No parallel v1 ledger is written.

Same operation ID and same input returns the original RECORDED result without
reapplying or a new audit. duplicate=true is authoritative; nested original
newReservation is historical data, not a new grant. All dispatchAllowed flags
remain false. Changed input under the same operation ID rejects. Transaction
exceptions block the current owner without compensating writes/retries.

inspect_v2 uses mode=ro and one read transaction, verifies meeting/packet and
optional expected ledger ID, bounded counts, IDs, hashes, replay, operation results
and final state. Every result forbids dispatch/restore. Open/pending/unknown is
blocked; terminal declarations are display-only. v1 is not migrated or fabricated.

## Limits

Serialized single-owner research only. No Pi/provider, credentials, process,
production wiring, multi-owner locking or writable reopen. The UUID and hash chain
do not prove trusted identity or prevent wholesale replacement. No original model
response, response-body receipt or opinion text is captured by this slice; results
are explicit synthetic status declarations. Completion is completed_declared only.
No executable recovery, cost accounting or external exactly-once guarantee.

A failing commit cannot reliably persist its own failure marker. Current owner
blocks; all later read-only inspections always deny dispatch regardless of whether
that commit appears. Missing operations do not prove an external call never ran.
Initialization failure can leave a partial new file; it is not deleted or retried.
Real crash, commit uncertainty, concurrency and WAL sidecar behavior are untested.
The synthetic unknown test is not evidence of a real fault. No full-schema/security
validation claim. No tests attempted writes through a read-only connection.

## Developer verification

Only the six individually reviewed new ordinary synthetic nodes below ran.
Temporary SQLite fixtures; no paused/security/write-refusal/browser tests or model/
process calls. The state/op/audit test observes normal committed data together;
it is not fault-injection rollback or crash testing.

```bash
/workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider \
 research/expert_budget/test_ledger_v2_candidate.py::test_new_meeting_operation_state_audit_visible_together \
 research/expert_budget/test_ledger_v2_candidate.py::test_same_operation_returns_recorded_result_without_new_audit \
 research/expert_budget/test_ledger_v2_candidate.py::test_stop_persists_progress_and_unresolved_request \
 research/expert_budget/test_ledger_v2_candidate.py::test_partial_budget_retains_prior_declared_role \
 research/expert_budget/test_ledger_v2_candidate.py::test_synthetic_unknown_remains_blocked_on_readonly_reopen \
 research/expert_budget/test_ledger_v2_candidate.py::test_v1_remains_unmodified_and_not_migrated
```

Result: **6 passed in 0.10s**, developer tests, independent review pending.
No other tests run. Real execution HOLD. No merge/deployment.

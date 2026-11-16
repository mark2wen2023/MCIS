# Isolated simulated V2HostProtocol

Parent: 019f379c220124457590b90bdc618aa1a4f3242b.

Actual chain: V2HostProtocol.handle -> NewMeetingLedger.apply -> revision-3
state/operation/audit transaction. No RequestBudget, DurableHost or v1 writer is
created or called. The legacy host and process paths remain unchanged. This new
host has no process/provider callback, runtime enable parameter or recovery API.

The caller supplies stable operation IDs. issue/model/result/complete_declared/
stop messages map to one ledger action. External model request ID is parsed into
its bound ticket/ordinal; result retains request ID, outcome and receiptDigest.
Ledger enforces the existing 2/16 quotas. State, allowance, receipt digests and
terminal reasons are sourced only from the new ledger, not duplicated in host
progress lists. Only a conservative local blocked flag remains in memory.

Outer duplicate is checked before nested historical newReservation. Duplicate
operation returns historical data with simulatedReservationCommitted=false and
blocks this host, without another write or overwritten stop reason. Different
operation IDs repeating a request use the ledger's durable protocol_duplicate
transition. Budget/unknown/explicit-stop outcomes block further messages. Prior
receipt digests and original terminal reasons are retained. All dispatchAllowed,
newDispatchGrant and executionVerified flags remain false, including fresh requests.
Fresh simulatedReservationCommitted only denotes successful declaration commit.

A BaseException guard covers message parsing and the entire ledger call, including
connection opening and interruptions; exceptions block locally without retries or
compensation writes. Constructor starts blocked and propagates initialization
failure. No construction/resume from an old file. This is code-path coverage by
inspection; actual connect/commit faults and interruptions were NOT executed.
Local failure/outer-duplicate block is not a new durable failure record; read-only
reopen still always denies dispatch. No persistent execution-recovery claim.

## Developer tests and limits

Six new individually reviewed ordinary synthetic message nodes only; temporary
SQLite data, no write-refusal/security/paused/browser/process/model tests. No
credentials, downloads or provider. Unknown is declared synthetic input. No real
crash/uncertain commit, concurrent caller, process ownership or full four-seat
end-to-end test this round. Completion remains declaration, not actual opinion or
execution. Actual Pi/provider/production integration HOLD, no merge/deployment.

```bash
/workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider \
 research/expert_budget/test_v2_host_candidate.py::test_only_new_ledger_and_receipt_path \
 research/expert_budget/test_v2_host_candidate.py::test_outer_duplicate_blocks_historical_reservation \
 research/expert_budget/test_v2_host_candidate.py::test_new_operation_duplicate_preserves_receipt_and_stop_reason \
 research/expert_budget/test_v2_host_candidate.py::test_budget_stop_retains_reason_and_prior_progress \
 research/expert_budget/test_v2_host_candidate.py::test_unknown_message_stops_without_retry \
 research/expert_budget/test_v2_host_candidate.py::test_malformed_message_blocks_without_added_operation
```

Result: **6 passed in 0.10s**, developer synthetic; independent review pending.
No other tests run.

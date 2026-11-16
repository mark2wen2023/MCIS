# Receipt and stop contract revision — isolated candidate

Parent: cc549214852abc63ad842a7297c5683e58dde21d.

The v2 ledger family now creates user_version=3 (receipt contract revision), so
new semantics are not silently applied to historical revision-2 audit events.
Existing revision-2 data is read-only replayed with legacy_advance unchanged and
receiptCoverage=unknown_legacy. v1 remains unsupported here and is not migrated.

New result actions must contain receiptDigest: SHA256-format string when outcome
is received_unverified, null when unknown. It is recorded in the action audit and
current request projection in the same operation/state/audit transaction. Repeated
result declarations cannot change the recorded digest. This stores a supplied
digest, NOT verified original bytes, provider identity or actual model execution.
No actual response payload has been introduced.

Same operation ID/input returns a historical result, duplicate=true and explicit
newDispatchGrant=false. No new audit or application. Nested recorded newReservation
can remain historically true; it is never a new grant. A different operation ID
for an already recorded request stops an open meeting with protocol_duplicate in
the same transaction; no new request is allocated. Already terminal causes stay
unchanged. All apply responses, not just duplicates, prohibit dispatch.

Stop actions distinguish operator_stop, protocol_duplicate, protocol_unknown.
Request unknown records request_unknown; quota exhaustion records budget_exhausted.
Later stop declarations preserve the first terminal state/cause and do not alter
prior receipts. They may add an audit of the repeated declaration. Completed
sessions are not relabeled stopped. Legacy missing causes are not backfilled.

No host/worker/provider integration or recovery is enabled. Single serialized
owner assumption remains. Connection-opening failure outside the existing apply
exception block remains a known boundary for a future host wrapper; this slice
makes no new commit-uncertainty guarantee. No real crash, concurrency, provider
receipt or unknown-commit validation. Pi/models HOLD.

Compatibility: new received-result callers must supply receiptDigest. Old revision-2
writer tests/callers that omit it need an explicit contract update; they were not
silently modified or run. Old revision-2 read-only audit replay remains supported.
The old frozen ledger hash is superseded by this candidate's new hash list; the
prior report describes its prior revision, not this implementation.

## Reviewed ordinary developer tests

Only the following six new nodes were run: temporary synthetic databases, normal
protocol validation and historical fixture replay. No write attempt through a
read-only connection, paused tests, security probes, process, model or browser.

```bash
/workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider \
 research/expert_budget/test_receipt_stop_candidate.py::test_receipt_recorded_in_state_and_audit \
 research/expert_budget/test_receipt_stop_candidate.py::test_missing_new_receipt_rejects_without_added_operation \
 research/expert_budget/test_receipt_stop_candidate.py::test_duplicate_operation_is_historical_not_new_grant \
 research/expert_budget/test_receipt_stop_candidate.py::test_repeated_request_new_operation_stops_atomically \
 research/expert_budget/test_receipt_stop_candidate.py::test_later_stop_preserves_budget_reason \
 research/expert_budget/test_receipt_stop_candidate.py::test_legacy_v2_receipt_absence_stays_unknown
```

Result: **6 passed in 0.11s**, developer synthetic only. Independent review pending.
No other tests run. Not pushed/merged/deployed at implementation time.

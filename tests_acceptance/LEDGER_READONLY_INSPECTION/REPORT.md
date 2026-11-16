# Isolated read-only ledger inspection

Parent: 751d32c08ff753b65232ea91282e782cef2d5c2b.

New inspect_ledger uses SQLite URI mode=ro, BEGIN and a single snapshot, closing
its connection on every return. It does not call RequestBudget constructors,
create/stop/snapshot or any write statement. Existing ledgers and host code are
unchanged. No initialization, migration, dispatch or resume is provided.

It checks expected meeting and fixed public packet, v1 tables/columns, bounded
whole-ledger enumeration, stable role/round ticket mapping, context format,
request linkage/IDs/order, receipt shape and 2/16 allowance. Unknown older ticket
mapping is blocked_unknown; inconsistent records are blocked_inconsistent.
Open plus received requests cannot establish role completion. Pending, unknown
and not_dispatched remain blocked. Recorded stop/budget status may be displayed
as recorded_stopped but NEVER grants dispatch or restore. All results retain
roleProgress=unknown_legacy_v1, dispatchAllowed=false, restoreReady=false and
databaseIdentityVerified=false. Remaining allowance is recorded count only, not
permission to use it.

This is structural/record consistency inspection, not authenticity validation,
full SQLite constraint/DDL verification, filesystem hardening or trusted database
identity. No original provider response exists here to verify its receipt hash.
No full role-completion history exists. New files are not created by our SQL;
WAL sidecar behavior across environments was not tested or guaranteed. No live
concurrent writer, actual crash/uncertain commit, external mutation or resume
was tested. No success/execution authorization classification exists.

## Developer tests

Eight individually reviewed ordinary synthetic nodes. Setup creates only temporary
fixture databases. No attempts to write through the read-only connection, no
write-refusal probes, paused tests, browser/process/model/API calls. One ordinary
rollback-journal fixture also compares database bytes before/after inspection;
this is not a general WAL or filesystem immutability claim.

Exact command from repository root:

```bash
/workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider \
 research/expert_budget/test_readonly_inspection_candidate.py::test_open_received_does_not_infer_role_completion \
 research/expert_budget/test_readonly_inspection_candidate.py::test_pending_and_unknown_are_blocked \
 research/expert_budget/test_readonly_inspection_candidate.py::test_recorded_budget_stop_is_not_resume_permission \
 research/expert_budget/test_readonly_inspection_candidate.py::test_expected_meeting_mismatch_is_blocked \
 research/expert_budget/test_readonly_inspection_candidate.py::test_older_ticket_mapping_is_unknown \
 research/expert_budget/test_readonly_inspection_candidate.py::test_three_requests_exceed_turn_budget \
 research/expert_budget/test_readonly_inspection_candidate.py::test_orphan_request_is_inconsistent \
 research/expert_budget/test_readonly_inspection_candidate.py::test_wrong_expected_material_is_blocked
```

Result: **8 passed in 0.11s**, developer synthetic tests only. No other tests run.
Independent review pending; real Pi/models HOLD. No merge/deployment.

# Consultation-only export refusal

Independent branch fix/consultation-export-refusal, parent
8dd3dc9ac19483d05ccb2125a229c38a7b24b15b (research) -> 4099d235 -> cf80623 ->
b23c7b6 -> e68bacc -> 2cb43812 -> main94d5e38. No push/merge/deployment this task.

## Reproduction and minimal fix

Before editing, reran test_consultation_archive_readiness.py on the exact parent:
4 passed in1.02s, including its known-gap characterization: consultation-only export
200/manifest1.0, restricted intake422 with unchanged destination. That passing
characterization was not an assertion that the export was safe/recoverable.

Production change: two lines in working_records_archive/service.has_history detect
ConsultationRoundRow for the selected case. This routes export through the existing
full-content authorization and unsupported-state preflight. The unchanged table
whitelist rejects consultation before assembly; export maps that failure to409
ARCHIVE_RESTORE_UNSUPPORTED. No archive support, serializer, parser, permissions,
policies or version schemas added/relaxed. Existing protect_recommendations still
runs first; unauthorized callers continue403 rather than seeing a new grant.

The same test now expects409/JSON/no ZIP, with all database tables and temporary
blob file hashes unchanged. Timeline+consultation remains409 without mutation.
Original source-binding and single-decision characterization tests remain. One new
ordinary test confirms Investigator/Public403 without database/blob changes.
The prior research report describes the historical gap; this follow-up supersedes
only that unresolved export-selection statement, not the missing source-binding gate.

## Developer validation

```
service/.venv/bin/pytest -q service/tests/test_consultation_archive_readiness.py service/tests/test_timeline_only_archive.py service/tests/test_timeline_import_origin.py service/tests/test_bounded_timeline_archive_increment.py service/tests/test_contracts.py service/tests/test_environment_w92.py service/tests/test_working_record_archive.py::test_three_store_roundtrip_and_inactive_receipts
```
96 passed in26.59s. Covers empty1.0 restore, supported timeline-only1.4 two restores,
working-record1.2 three-store history, report+timeline1.4, existing origins and ordinary
rollback/refusal/permission checks. No skips/failures in this selected group.
After adding explicit blob file hashes to the consultation rejection snapshots,
reran the final5 consultation tests separately: **5 passed in0.81s**. Runtime code
unchanged since the96-test run. All data synthetic; temporary apps/directories/SQLite.

No frontend change/build/browser test in this task. No full suite, real identity,
load/crash behavior, HFACS/model execution or independent acceptance claim. Prior
baseline failures not rerun or claimed fixed. No previously restricted historical
integrity or ECFC operation repeated. Complex consultation cases remain unsupported;
this fix refuses a misleading success, it does not make them restorable. No automatic
retry, deletion, data migration, source inference or newly confirmed historical claim.

# Normal synthetic metadata continuation

2026-11-18, developer-only. Parent `a4f3044b2bef2a2d5e9a94b311d249b91de90334`, research/restore-normal-case-registration. Only a new ordinary test and this record; no product changes.

Coverage gap: the existing W8.4 ordinary workflow checks a single legacy import; the previous artifact test has no metadata edits. The new node exercises metadata A, supported 1.2 export/intake into a fresh store, metadata B with the returned revision, then export/intake into a third store. Checks exact snapshot/revision/lastChange retention, declared source/reason, unchanged original metadata audit line, second line before/after values, and immutable case/time/location/fiction fields. No claim that user-declared source is independently verified.

Static call review before execution: case_metadata/router.py GET/PATCH uses existing readable/write policies and snapshot/apply_changes/audit.append; it has no model calls. package_intake/router.py commit_sync uses the existing parser/staging/import path; working_records_archive/service.py preserves original intake artifacts/history. Initial package is fictional and contains no HFACS member/state. hfacs_drafts/archive.py build returns None for empty current/events/receipts, before core validation. Helpers imported only from the already-reviewed ordinary artifact test and conftest; no denied-request or fault-injection helper invoked. No production directory, server listener, browser, real materials, core/model execution, paused nodes or write-refusal probes.

Exact command from service/ using existing dependencies:
```
/workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q tests/test_archive_metadata_continuation_normal.py::test_metadata_edit_after_restore_retains_versions_sources_and_audit
```
Result: **1 passed in 0.86s**, first execution. Only this node ran; no combined count with earlier tests. Three tmp_path stores, seed_demo=False, in-process FastAPI TestClient; existing self-reported LeadInvestigator header fixture is not production authentication. All ZIPs/SQLite data remain temporary and are not committed.

This establishes a limited ordinary metadata continuation path on this research tree, not full complex-case restoration or main/PR104 acceptance. No evidence registration/bytes, HFACS, concurrent writers, crashes, unknown commits, complete lineage revalidation or browser testing in this node. Prior independent acceptance applies to a4f3044's artifact node, not this addition. Unsupported-state protections and permissions unchanged; no merge/deploy.

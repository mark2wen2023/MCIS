# Actual temporary SQLite continuation: bounded developer evidence

Base6f7eb94c5a01af1ba7295e42c5caa1f05399e1d2; restore scaffold derives from a812d38
conflict_sandbox.py. Research module only, no product imports/routes/table registration
or archive policy changes. New separate SQLite table holds inactive receipt entries.

Command from service/:

    PYTHONPATH=.. .venv/bin/pytest -q tests/test_conflict_v2_sqlite_continuation.py tests/test_conflict_archive_envelope_v2.py tests/test_conflict_archive_receipts_v2.py tests/test_conflict_restore_current_compatibility.py

New targeted run11passed3.65s. Expanded result recorded in REQUESTS.md after completion.
Actual TemporaryDirectory/SQLite, actual existing domain ConflictPatch/CAS/capture/audit,
synthetic ordinary source bytes and registry only. No mock restore result. Domain route
functions are called directly with declared-role context, not HTTP or browser.

Main scenario: v2 ZIP with two captured revisions and consumed+unused receipts ->
first DB -> append note -> actual row-based export -> second DB -> append another note
-> export -> third DB. Exact imported revisions, original audit prefix, custody,
evidence registration and inactive receipts retained. Active receipt table empty in
first and third DBs. Member validation checks audit/source/version associations on
both reconstructed exports; source raw synthetic bytes preserved. Export only allows
existing conflict note/status continuation; active/new receipts and other state refused.

Six restore fault checkpoints prove every table/BLOB unchanged after ordinary exception;
explicit retry follows known rollback. Append-failure test records a marker after actual
capture succeeds, then injects failure and compares all tables. No broad500-only false
positive. Separate v1/v2 synthetic no-history input remains unknown through new note
and another restore; no fabricated source history. Existing destination overwrite
refused. Minimal ordinary1.0 ZIP remains accepted by existing parser but refused by
this research store (all rows unchanged). Other production old format combinations
were not regression-tested here.

Limits: no product filesystem paths, product import receipt, durable multi-import
origin mapping/readiness, concurrency/crash/unknown-commit or whole-system acceptance.
Prior package BLOB in each destination is that import's source ZIP; a durable recursive
lineage of earlier original ZIPs is not promised. Historical fields and raw audit
remain retained, but no trustworthy actor identity or original-byte authenticity claim.
No real original accessed; only synthetic fixture bytes. No restricted security/ECFC
operations, production restore, browser, merge or deployment. restore_ready=false.

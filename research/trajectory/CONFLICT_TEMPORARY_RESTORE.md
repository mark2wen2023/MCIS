# Disposable conflict restoration candidate

Base1d41874704cd16d68854f3f6c9f45f0780a55951; branch feat/conflict-temporary-restore.
No product import/export wiring or source permissions changed. New sandbox owns a
fresh temporary SQLite store and cannot accept a product storage root or DB argument.
Original source ZIP and member bytes are SQLite BLOBs in the same transaction as
restored rows. No original file publication/compensating filesystem deletion.

## Actual reconstructed data

Exact conflict key/doc/created/updated timestamps and every captured revision, original
audit/custody lines with their index columns, evidence registration documents, default
policy, case and vessels. Legacy empty/partial journal remains unknown-before-capture;
no earlier actor/source is invented. Re-export reads the database, validates it against
the retained snapshot and reconstructs a newly checksummed experimental envelope.
New DB integer row IDs and non-conflict ORM timestamps are not archived originals.
No new human action is replayed. Research receipt is local bookkeeping, not an active
product request. No multi-hop import lineage is newly claimed in the next package.

## Developer tests

Initial local11-test group:10 failed/1 passed because research inventory mistakenly
used `conflicts` instead of actual ORM table `timeline_conflicts`. Fixed by using
ConflictRow.__tablename__. No product protection/table allowlist was changed.
Corrected local group:11 passed in3.05s.

Expanded command:
```
service/.venv/bin/pytest -q service/tests/test_conflict_temporary_restore.py service/tests/test_conflict_archive_envelope.py service/tests/test_conflict_archive_parser.py service/tests/test_conflict_archive_dependencies.py service/tests/test_package_intake_parser.py service/tests/test_contracts.py service/tests/test_timeline_only_archive.py service/tests/test_working_record_archive.py::test_three_store_roundtrip_and_inactive_receipts
```
145 passed in27.15s. Included normal-exception rollback after current rows, journal,
audit, objects and pre-commit reconstruction; every table/BLOB unchanged then explicit
retry succeeds. Two concurrent connections restore to the same fresh store: one succeeds,
one refuses existing target, no overwrite. Existing history reader accepts declared
LeadInvestigator and rejects Investigator403 using restored policy; this is not SSO.
Old package parser/working-record and bounded timeline ordinary compatibility tests
included. Unsupported populated state prevents re-export.

Final test-only enhancement adds a third actual conflict revision to the two-restoration
case and a malformed-ZIP preparation-zero-write test. Exact final command:
```
service/.venv/bin/pytest -q service/tests/test_conflict_temporary_restore.py::test_two_restore_roundtrip_exact_business_and_bytes service/tests/test_conflict_temporary_restore.py::test_invalid_preparation_does_not_create_rows_or_objects
```
2 passed in0.85s. Runtime code unchanged after the expanded145 checks. Do not
add the targeted test count to145 as distinct full-suite coverage. All fixtures are
synthetic, source package assembled explicitly in test memory; product did not export
conflict cases. Original packaged bytes, three revision snapshots, exact conflict row
timestamps and original audit/custody lines are compared across two stores/re-exports.

## Remaining limits

Return remains restore_ready=false for product usage. No production route accepts this
experimental profile. Source export409 and experimental intake422 remain in regression.
Temporary clone is frozen: subsequent business edits are rejected on re-export, rather
than silently discarded. Live continuation, product filesystem reconstruction, complete
combined-case support, historical-source authorization integration and import receipt
lineage need further design/review. Historical registry digests are declarations;
bytesVerified=false does not become actual historical original verification.

No independent/browser/real-case/production acceptance, full-system tests, disk/commit
failure or process-crash testing. SQLite transaction failure tests do not prove unknown
commit outcomes or cross-filesystem atomicity. This temporary directory is deliberately
disposable at context exit. No automatic product retry/cleanup. No restricted security
or ECFC tests; no merge, deployment or push this turn.

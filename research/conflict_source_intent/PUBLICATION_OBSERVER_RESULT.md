# Product-layout observation: developer result

Base5c303df9a4f4e907ff03b78ad11de5c553047363, branch
research/conflict-publication-observer. Remote main read this turn remains
94d5e38c926fda232bb987b60fa9145e4bcf01a7. No repository .agents directory or
/workspace/.agents skill files found; AGENTS and handoff consulted.

New code publication_observer.py uses actual existing SQLite operation/commit
markers and retained source, not a new simulated ledger. Mapping matches static
mcase.import_case raw/evidence writes and intake source.mcase retention. Only
synthetic fixtures materialize the directory/operation.json, no production
publisher or recovery route. API reports observational match, always not-ready.

Command (service/):

    PYTHONPATH=.. .venv/bin/pytest -q tests/test_conflict_publication_observer.py tests/test_conflict_commit_observer.py tests/test_conflict_v2_sqlite_continuation.py tests/test_conflict_archive_envelope_v2.py tests/test_conflict_archive_receipts_v2.py tests/test_conflict_restore_current_compatibility.py

New tests: matching/missing/differing/extra files, different operation marker,
journal/before_commit exception rollback, response loss after successful commit,
missing database, WAL committed snapshot during writer, invalid synthetic DB.
Fresh subprocess inspection verifies reopening, no original files or restricted
security/ECFC probes. Inventory/DB counts show inspection does not mutate fixtures.

Initial expanded run75passed/1failed: test incorrectly assumed BEGIN EXCLUSIVE
would block readers in the existing WAL configuration. Corrected that ordinary
test to assert committed-snapshot observation and added malformed synthetic DB
unknown/no-modification coverage. Not a change to database or security settings.

No genuine process crash, power-loss, fsync, parent-directory race, or actual
SQLite uncertain-commit test. Response-loss exception occurs after commit; it is
not proof of those cases. The observer is read-only and makes no unknown outcome
safe to retry/delete. No durable ready transition/entry gating/publisher enabled.
No existing normal case hidden, experimental archives still rejected. No browser,
production identity, real-case, or independent acceptance. See contract for
remaining binding/exclusion/durability/integration requirements.

Final expanded run:77passed in27.71s, including11new tests and66existing tests;
not separate independent acceptance and not full system testing.

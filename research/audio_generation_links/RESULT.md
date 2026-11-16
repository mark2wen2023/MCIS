# Isolated generation/observation association validator

Parent 88263f5f9fe7e7722df85235976696548828cb4c. New internal module only: no routes, model migrations, existing preflight/adapter/whitelist edits or archive enablement.

`inspect_case` requires the caller's clean SQLite session and reserved writer, reuses existing intake and full-archive permission checks, and queries each of four tables with the same case ID in that transaction (10000-row per-table limit). It does not read originals or task directories, execute tasks, or write records. `validate_rows` is a pure structural helper; it cannot establish inventory completeness for caller-supplied arbitrary rows.

Checks cover one generation per task, generation source equality with task snapshot, exact observation fields, supported ordinal set per task status, audit case/sequence/line digest/action/command/entity/operator/role, ordering and no reused/unmapped ASR lifecycle audit. Missing generation explicitly rejects as legacy-or-lost-history unknown; no backfill. Missing/duplicate/orphan/inconsistent records reject. Unknown writer closure and absent manifest are preserved; running/failed/interrupted records may have internally consistent associations but never archive readiness.

This is not full audit hash-chain verification, original-byte verification, registered-source authenticity, completion proof, or database tamper protection. It does not recheck every Revision/run or registry association: existing media validators remain necessary. New-format member preservation is not implemented. Existing media preflight and audio extraction still reject these new tables; no fallback that omits them. archiveReady=false, restore_ready=false, historicalProof=false for every accepted result. This checker is not a replacement for a provenance or authorization boundary.

Developer validation: 8 distinct explicitly selected new ordinary synthetic nodes in two runs (6 passed in 0.34s, then 2 passed). One uses temporary native tables and a stub recognizer; remaining nodes use constructed rows. No real audio/model run, browser, paused test, write-refusal probe or security test. No concurrency/crash/production identity certification. Independent review pending.

Exact executed commands from repository root:
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_audio_generation_links.py::test_same_transaction_native_task_links_stay_not_ready service/tests/test_audio_generation_links.py::test_missing_generation_is_unknown_not_backfilled service/tests/test_audio_generation_links.py::test_orphan_and_duplicate_observations_rejected service/tests/test_audio_generation_links.py::test_incomplete_and_source_mismatch_rejected service/tests/test_audio_generation_links.py::test_audit_reference_and_digest_must_agree service/tests/test_audio_generation_links.py::test_running_observation_is_consistent_but_unresolved --tb=short
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_audio_generation_links.py::test_duplicate_generation_and_case_disagreement_rejected service/tests/test_audio_generation_links.py::test_incomplete_observation_matches_recorded_status_only --tb=short
```

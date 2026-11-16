# Internal generation-aware audio member assembly

Parent 435ce9037aff410fa6b7e36215c3aa5bd5d185da. Standalone isolated modules; original preflight.py, archive_candidate.py, media contracts, product export routes/whitelists and permissions unchanged.

## Actual code chain
`generation_assembly.build_candidate` requires the caller's clean reserved SQLite writer session and existing intake/full archive policy. `generation_inventory.scan` enumerates same-case rows in that connection, validates every task/generation/observation/audit association before recognizing the two added tables, then retains existing audit-chain, registration and revision association checks. It refuses any other unknown media state. Assembly refuses non-supported case tables, missing/unfinished task runs, legacy missing generation, unrelated evidence and missing source receipts. No table is admitted merely by its name without linkage checks.

Registered audio is read with existing authorized load_receipt once per receipt, cached within the call and checked against saved digests/sample clock. The v1 base retains all captured revisions, raw model results and complete case audit lines; v2 adds each generation and observation as an explicit checksummed member. New records retain case/task/generation/ordinal/doc and exact audit reference; local Observation.id is not an archival identity and is not encoded, while full source rows remain in nativeInventory. Native task directories/log/HOME are NOT read or included. These unresolved files prevent this from being a complete archive.

Both source-byte validator and generation-format validator run before returning an in-memory result. All export/restore/execution flags remain false; writers remain unknown. No ZIP, publication, restoration, worker execution or cleanup is introduced. This is not a complete case package and must not be used as an alternate export bypass. Old extraction still refuses new tables as before.

## Maintenance and limitations
To obey the instruction not to modify the old extractor/preflight, new modules explicitly fork their existing code and add scoped validation/assembly. This duplicates logic and creates drift risk; any future shared refactor needs a separate review preserving old behavior. This does not prove immutable filesystem snapshots, writer closure, historical authenticity, production identity, concurrency or crash semantics. No production data or browser validation.

## New ordinary developer tests
6 unique explicit nodes: first five passed in 1.63s; final legacy node passed. Synthetic PCM, stub recognizer, disposable SQLite only. Exact stored generation/observation projections and two human revisions checked; two tasks share one receipt read; missing receipt, failed task, unsupported business state and missing legacy generation refused. No old test nodes, whole files, paused tests, safety/write-refusal probes or browsers executed. Independent review pending.

Commands from repository root:
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_audio_generation_assembly.py::test_native_generation_observations_and_revisions_are_retained service/tests/test_audio_generation_assembly.py::test_two_tasks_keep_all_histories_and_one_source_read service/tests/test_audio_generation_assembly.py::test_missing_registered_member_refuses_component service/tests/test_audio_generation_assembly.py::test_unfinished_task_is_not_omitted_or_restarted service/tests/test_audio_generation_assembly.py::test_other_business_state_remains_unsupported --tb=short
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_audio_generation_assembly.py::test_legacy_task_without_generation_stays_unknown --tb=short
```

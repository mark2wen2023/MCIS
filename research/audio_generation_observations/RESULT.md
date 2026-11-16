# Isolated generation/observation persistence

Base: 8687ec9f0737008b0345cf9fef443a5e9671f94a. Only optional audio-review app wiring; default app, permissions, response documents and archive whitelist unchanged.

## Implementation
Two additional Storage tables: audio_task_generations (unique task, random generation identity, registered source snapshot) and audio_task_observations (generation + ordinal unique). Both include case_id. Existing task/start audit and generation/ordinal0 commit together before dispatch. Existing final task/result/success audit and ordinal1 commit together; exception/timeout observations share the incomplete-state/audit transaction. Audit case/task is checked, sequence and full audit line digest retained. No audit payload truncation dependency. No new public route or fields; no logs, model outputs or credentials in observations.

Observation names describe only what the service control flow observed: registration, timeout exception, execution-or-conversion exception, or converted result and rechecked source. No stored claim that an OS process exited or all writers closed. Every observation retains writers=unknown, manifestStatus=not-captured, archiveReady=false. A successful ASR result remains distinct from archival readiness.

## Migration and failure boundaries
Existing optional app create_all adds tables without changing existing columns or backfilling tasks. No default-app initialization changes. Missing new-generation records cannot be synthesized by observe(). Test covers legacy-shaped task surviving app reopen with no backfill, NOT a deployed old-database migration or mixed-version multi-process deployment. New rows use insert-only application paths but there are no new DB append-only triggers/FKs; this is not tamper-proof storage or a completed migration mechanism.

No filesystem changes/publication/cleanup added. Injected final transaction failure rolls back observation, result revision, success audit and status; initial registration failure leaves no task/generation/start audit and never dispatches. These are ordinary exceptions after flush, not process crashes or uncertain SQLite commits. Real unknown commit/restart reconciliation remains unimplemented; database commit return is not stored as speculative confirmed evidence. Missing terminal observation remains unresolved; no automatic replay, delete or repair. Files may remain from interrupted work. Writer ownership/closure, durable file manifest and atomic publication remain blockers; formal archive/restore still prohibited.

## Developer validation
6 unique, individually selected NEW ordinary synthetic nodes: first 4 passed in 1.14s; next 2 passed in 0.65s. Synthetic WAV and stub recognizer only. No actual ASR, audio inspection, browser, paused tests, security probes or write-refusal tests. Fault markers explicitly prove the intended flush point was reached. Independent review pending.

Exact commands from repository root:
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_audio_generation_observations.py::test_success_records_observation_without_public_or_completion_claim service/tests/test_audio_generation_observations.py::test_exception_and_timeout_are_not_exit_proof service/tests/test_audio_generation_observations.py::test_observation_fault_rolls_back_final_state_and_audit service/tests/test_audio_generation_observations.py::test_existing_task_is_not_backfilled_on_reopen --tb=short
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider service/tests/test_audio_generation_observations.py::test_ordinary_exception_preserves_incomplete_observation service/tests/test_audio_generation_observations.py::test_registration_fault_does_not_dispatch_or_leave_partial_generation --tb=short
```

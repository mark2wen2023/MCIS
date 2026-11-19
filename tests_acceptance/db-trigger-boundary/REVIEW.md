# Private database append-only trigger installation boundary

Base: 4a1a8005b74b85b36a4a20550bb03667d7933786 on candidate/media-demo-lazy-factory.

Only product edit: Database.create_all delegates its original trigger transaction block to private _install_append_only_triggers(self). Full models_registry import and Base.metadata.create_all remain unconditional and in their original order. No table subset, skip flag, trigger parameter, alternate initialization path, model or permission change. APPEND_ONLY_TABLES remains audit_events then custody_events; each installs UPDATE then DELETE, same SQL text, same engine.begin transaction. Errors are not caught/replaced. The private method is not an approved independent runtime entry point.

## Bounded source dependency findings

These are scoped call-chain requirements, NOT an exhaustive safe-to-run minimal schema or a proposal to omit other tables:

- cases/service.py load_case/list_cases read cases; cases/router.py creation stores CaseRow and appends audit. Other endpoints in that same router (overview/vessels etc.) have extra tables, so importing/mounting the entire router is broader than basic case read/create.
- evidence_intake/router.py authorize requires an existing case, evidence_meta/testimony access levels and restricted-evidence policy; these depend on cases and access_policies. common/context.py still uses role/operator headers, not production authentication.
- load_receipt requires evidence_items and custody_events, verifies the Register binding and current bytes, and calls working_records_archive.service.archived_evidence BEFORE ordinary receipt lookup. That helper (service.py:185–192) queries archive_import_history for evidence-intake history. Its table has after_create append-only UPDATE/DELETE protection in working_records_archive/models.py; omitting the history query/table would weaken existing historical-original rejection.
- Registration/access/human review append custody/audit records; audit_events/custody_events require their unchanged DB triggers. Both are still installed by full create_all, not bypassed by this extraction.
- Image storage is image_ocr_review_records; audio storage audio_review_revisions; their private initialization helpers preserve module-specific triggers. Default register also imports task modules before Storage.create_all: image_ocr_tasks, audio_asr_tasks, audio_task_generations and audio_task_observations consequently belong to the current registration/model surface even when runtime is None. They cannot simply be omitted on the assumption that no model task is requested.
- Report *record* tables investigation_reports/report_operation_snapshots are used by report read/generation/export, not queried by the basic ordinary receipt branch examined here. However report *access protection* is already required for historical receipts (load_receipt calls require_content before historical_only) and ZIP-like original downloads (report_output/attachment_access.py protect_container). require_content uses access_policies and begin; it is not safely deferrable wholesale to report export.
- Import closure remains broader than the query minimum: working_records_archive.service imports other archive/report/interview models and validation; models_registry loads the full business model set. Archive model event hooks are separate from this extracted DB helper. Existing writes, snapshots and guards require further review before any smaller registry/factory can be proposed.

## Development check

`python tests_acceptance/db-trigger-boundary/check.py`

Passed three old/new handmade-engine sequence comparisons: normal, create_all callback error, first trigger execute callback error. Only extracted methods are compiled, with fake registry importer, metadata, engine/context and text function. No Database constructor, ORM, SQL or application executes. Normal events preserve registry → tables → begin/enter → four SQL strings → exit. Table error occurs before trigger transaction; trigger error propagates the same sentinel through context exit without further execution. These are synthetic callbacks, not actual DB fault injection or permission/write-refusal tests.

Expanding the private helper restores the complete old db.py AST. All original text(...) source expressions and rendered four SQL strings match exactly. Fixed local baseline Git object required, no automatic fetch. No previously paused tests or live operations run.

Awaiting independent review. No actual DB schema, triggers, locks, transactions, permission behavior, original bytes, HTTP, model/browser or isolation validated. main still constructs the full DB; media factory still delegates to main; request-time archive/report checks remain. Startup/archive pauses remain. No main/AI Studio/deployment changes.

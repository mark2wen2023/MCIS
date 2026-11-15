# Entry inventory and isolated pending gate

Base68c3e4ae3215a9b30be2b0c3c028bf830daf9c4b. No production modules changed.
Remote main read this turn:94d5e38c926fda232bb987b60fa9145e4bcf01a7.

## Static entry inventory

| Entry family | Actual source and required future gate |
| --- | --- |
| Case list | cases/router.py:list_cases -> cases/service.py:list_cases; filter explicitly pending restored cases only, preserve old ordinary rows |
| Case GET/overview/vessels/tracks and metadata | cases/router.py -> load_case; case_metadata/service.py also load_case; shared gate here is necessary but insufficient |
| Timeline/conflicts, environment, interviews/manual interviews, recommendations, agents, simulation, colreg, track import/history, access workbench, audit/redaction | route/service calls to load_case; must retain their existing permission checks and transaction semantics |
| Old evidence detail/edit/custody/access/verify/content | evidence/router.py has direct load_item/ledger paths without load_case, including get_content; cannot rely on case service alone |
| Evidence intake preview/commit/receipt/detail/download | evidence_intake/router.py:authorize -> load_case; commit/download reauthorize inside transactions; readiness must use that same session |
| Working-record evidence/provenance | working_records_archive/router.py requires content and load_case; service.py also reads CaseRow directly |
| Report list/create/read/generate/review/audit/snapshot/export/GISIS | reports/router.py:check_access -> reports/service.py:case_info -> load_case, with public-YANGZE missing-row special handling; report-template case query is separate; no restricted tests executed |
| Whole-case export | package/router.py:export role gate + IMMEDIATE -> mcase.export_case directly reads CaseRow; not covered by load_case |
| Old import and verify | package/router.py:import_package -> mcase.import_case uses body-derived case ID and direct CaseRow collision checks; verify reads bytes only, not live case access |
| Intake preview/commit | package_intake/router.py parses body case ID and checks CaseRow directly; restore operation claim must precede exposed restored rows; existing IntakeReceipt is not a ready protocol |
| Intake receipt by digest | package_intake/router.py:receipt resolves IntakeReceipt.case_id or archived history, then existing permission/source checks; digest-to-case resolution cannot be covered only by URL case parameters |
| Other direct case access | bowtie_preview, hfacs_drafts, nomoto_preview, human_factors_preview get_doc(CaseRow); seed modules create rows directly; internal mcase/build_files/export and working_records_archive/service likewise bypass shared load_case |

Inventory uses source searches for CaseRow, load_case, route decorators and receipt
handlers. It identifies concrete bypasses, not proof of universal HTTP/service gate
coverage. No browser, permission probe, real files, or restricted ECFC tests.

## Implemented isolated slice

PendingReadinessStore extends the actual temporary SQLite restore/commit observer.
Its waiting_publication row is inserted in the SAME session/transaction as restored
rows, inactive receipt history and commit marker. Failure before commit rolls all
these back while retaining the earlier claim. There is no ready promotion API.

One shared decision treats either a claim or a readiness row as hold, even an
unrecognized/ready state string; SQL failure raises unknown instead of legacy or
empty success. No claim/marker passes through to existing policy (not authorization).
Actual cases.service list/load are exercised through isolated wrappers. A generic
scoped_call test uses an explicitly synthetic callback to demonstrate nonexecution;
this is NOT product export/receipt HTTP integration or a replacement permission gate.
Existing app imports none of this module. Ordinary cases are not newly hidden in
production, experimental restore/import protection remains unchanged.

## Required before production

1. Durable deployment protocol/version migration must distinguish true legacy DBs
   from lost restore ledgers. Missing both research tables is only legacy-compatible
   in this isolated contract; corruption cannot safely be inferred as legacy.
2. Commit-bound publication manifest, ownership/exclusion, fsync/no-replace and
   post-restart checks remain unimplemented. 68c3e4a observation is not ready proof.
3. Same-transaction gate wiring at every entry above, including body/digest-derived
   case IDs and direct services, plus writer/reservation exclusion. Merely sharing
   a Session object does not prove every SQLite read is an explicit snapshot.
4. Preserve existing policy and normal metadata-only cases; introduce no role or
   original-file entitlement via readiness. Unknown results remain non-success,
   no blind deletion or retry. Independent endpoint/compatibility validation needed.

New8tests passed5.24s: old DB no research tables; mixed pending/legacy cases;
atomic pending row and fresh-process reopening; two rollback phases; response
loss after actual commit; held boundary; orphan/ready-label conservative handling;
malformed schema unknown. Parametrization means8pytest cases. All synthetic.
No actual process crash, ambiguous SQLite commit, production identity, browser or
full-app test. New subprocess opens persisted DB; response-loss hook fires after
actual commit, not during commit. No merge/deploy or restricted tests.

Expanded command (service/):

    PYTHONPATH=.. .venv/bin/pytest -q tests/test_conflict_readiness_gate.py tests/test_conflict_publication_observer.py tests/test_conflict_commit_observer.py tests/test_conflict_v2_sqlite_continuation.py tests/test_conflict_archive_envelope_v2.py tests/test_conflict_archive_receipts_v2.py tests/test_conflict_restore_current_compatibility.py

Final85passed31.73s includes the8new tests, not85+8 and not independent acceptance.

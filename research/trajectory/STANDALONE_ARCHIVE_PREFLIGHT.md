# Standalone unsupported-state export preflight

Base a7ce17bce4a74cf998fb3241efad12889779905f; independent branch
fix/standalone-archive-preflight. Remote main read-only checked94d5e38. Dependencies
are the previous bounded archive/refusal candidates, not merged main. No push here.

## Read-only inventory and observed baseline

Compared models_registry, package/mcase.build_files/export_case,
working_records_archive.has_history/reject_unsupported_tables and
package_intake/parser.empty_sections. Legacy1.0 assemble has no unconditional
parse_package preflight. Only key=current COLREG is serialized; simulation commands
are not serialized. Other nonempty legacy business members are rejected by intake.

Before runtime edits, six new refusal tests failed because export returned200. Ran
normal HTTP export/intake against isolated temporary synthetic cases on exact base:

| Sole state | Creation | Export | Restricted restore |
|---|---|---|---|
| Recommendation | ordinary POST; synthetic cause label |200/1.0|422 PACKAGE_INTAKE_INVALID|
| Timeline conflict | ordinary POST, two synthetic observations |200/1.0|422 same|
| Agent timeline draft | ordinary POST, synthetic payload/quote, no model |200/1.0|422 same|
| COLREG current row | direct ORM storage fixture, not computed result |200/1.0|422 same|
| COLREG inputs row | direct ORM storage fixture, not computed result |200/1.0|200, zero COLREG rows restored|
| Persisted pause command | ordinary POST, no Unity connected |200/1.0|200, zero command rows restored|

The COLREG fixtures demonstrate selection/serialization behavior for existing table
keys; they do not establish that real core evaluation ran or its output was valid.
Simulation queue omission must not be “fixed” by replaying active commands. Existing
working-record archives already refuse sim_commands; standalone cases now get that
same conservative refusal. This tightens export availability after persisted playback
commands and needs independent product review, not a claim of command backup support.

## Minimal implementation

has_history checks case-scoped existence of RecommendationRow, ConflictRow,
AgentDraftRow, ColregAnalysisRow and SimCommandRow alongside existing consultation
and timeline detection. They enter the existing full-content authorization and
closed-world table validation. These remain unsupported tables and return409
ARCHIVE_RESTORE_UNSUPPORTED before package/export audit creation. No table whitelist,
parser, schema acceptance, content permission, role, file reader or core code changed.
No new per-state serializer, no automatic retry/cleanup or data removal.

## Executed coverage

New13 ordinary tests: six standalone refusals, six Public403 checks, one same-table
other-case isolation test proving a normal empty case still exports1.0 and restores.
Refusals compare every database table plus temporary blob-file SHA256 snapshots;
no success ZIP returned. Existing regressions cover consultation-only/mixed refusal,
empty1.0, report/interview/history1.2, timeline-only and report+timeline1.4 with repeated
restores, prior origin bindings, permissions and ordinary injected rollback.

Command:
```
service/.venv/bin/pytest -q service/tests/test_standalone_archive_preflight.py service/tests/test_consultation_archive_readiness.py service/tests/test_timeline_only_archive.py service/tests/test_timeline_import_origin.py service/tests/test_bounded_timeline_archive_increment.py service/tests/test_contracts.py service/tests/test_environment_w92.py service/tests/test_working_record_archive.py::test_three_store_roundtrip_and_inactive_receipts
```
Final selected result: **109 passed in28.94s**, no failures/skips in this group. Only synthetic data. Baseline six failed
refusal assertions are resolved by the selection change, not removed or skipped.

## Coverage boundaries (not an exhaustive safety audit)

- Source inventory covers registered case tables, known legacy serialized members
  and the current allowlist/global exclusions. This is not arbitrary unknown-table,
  unknown-file or future-extension detection for every legacy path.
- HFACS1.1/core execution and track-history1.3 standalone workflows not freshly run;
  their existing selection code is unchanged. No production credentials/real cases.
- Evidence revision/missing raw files, policy mutations, audit-only orphan business
  events, receipt-only malformed states and historical integrity not probed here.
  Existing guards are not claimed independently revalidated by these tests.
- COLREG runs/annotations keys share table-level detection but only current/inputs
  fixture keys executed. No C# core, real vessel/AIS simulation or model evaluation.
- Global knowledge tables are outside case package; memory-only sim state is not
  persisted case data. Neither is changed/tested as new backup content.
- ECFC and previously restricted security/other operations not inspected/executed.
  No claim that all complex cases or every potential loss path is now covered.
- No browser/UI/build, full-suite, performance/memory/crash or independent acceptance.
  Prior baseline failures not rerun or called fixed. No merge/deployment.

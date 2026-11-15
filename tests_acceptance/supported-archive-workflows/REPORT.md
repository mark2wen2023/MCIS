# Ordinary supported archive workflow fixtures

Parent88cc9fdc4ed59704a1777aa58b0e16e058cf9220 (PR104 exact aggregate), independent
branch test/aggregate-supported-archive-workflows. No production change, policy
change, archive whitelist extension, seed deletion, SDK installation or mock HFACS.
Parent remote/main read unchanged88cc9fd/94d5e38. PR104 not modified.

## Basis and preserved assertions

The metadata test's purpose is editing five permitted fields, preserving immutable
fields/other records, exact before/after audit and restoration of a supported
case. Vessel test checks creation, source labels/parameters, named operator and
archive vessel content. Neither requires the demo's unrelated unsupported histories.

Existing research test a14321d /8ca8a8c:tests/test_archive_supported_boundary.py
already demonstrates supported synthetic metadata+vessel archive roundtrip. It is
read-only reference here, not cherry-picked with its unrelated stack. Current
contracts/W8.4-case-metadata.md '既有案件包标准化边界（D01裁定）' explicitly says
revision need not survive omitted-field normalization. The new local fixture
uses explicit legacy fields; it does not change normalization or promise arbitrary
sparse records keep their revision. Both modified test files were byte-identical
to exact main before this candidate; prior3-failure baseline remains applicable.

Only these two functions use the new supported_archive_client fixture: fresh
seed=False temporary app, POST-created synthetic case with existing CASE constant,
no deletion/filtering of existing demo data. All other tests retain their previous
fixtures. Ordinary edit requests still use Investigator; full audit/export/import
steps use explicit LeadInvestigator and check response status before parsing.
AST comparison confirms all13original metadata and7original vessel assertion
structures remain present. Added list-shape/status checks, vessel audit-chain check,
and actual import/re-export vessel equality. Prior bare-dict fallback was parsing,
not a removed assertion. Existing denial tests elsewhere are untouched.

Separate default seeded-demo tests assert Lead export409 with
ARCHIVE_RESTORE_UNSUPPORTED, JSON rather than ZIP, no attachment response, and
unchanged complete temporary DB rows/file digests. Also assert default Investigator
audit/export403 and unchanged state. This does not make complex archives supported
or clear demo contents to produce a passing archive.

## Actual developer commands/results

From service using existing .venv:

    ./.venv/bin/pytest -q tests/test_case_metadata_w84.py::test_read_update_audit_original_and_roundtrip tests/test_vessel_entry_w91.py::test_create_reopen_export_and_audit tests/test_archive_workflow_boundary.py

4passed2.26s, actual TestClient/product handlers/temporary SQLite, synthetic only.

    ./.venv/bin/pytest -q -rs tests/test_contracts.py tests/test_case_metadata_w84.py tests/test_environment_w92.py tests/test_track_history.py tests/test_vessel_entry_w91.py tests/test_archive_workflow_boundary.py

Final expanded result below. No automatic new skip/xfail. The previous aggregate
related group was187passed3failed; the same3 failed on exact main, documented in
preserved tests_acceptance/pr96-pr102-integration/REPORT.md. Genuine HFACS dependency
was not replaced, faked or skipped by this change.

No real cases/original files, production identity, browser or full-system/CI test.
No restricted historical-integrity/security/ECFC operations retried. No merge,
deploy or change to existing PR. Prior333/1skip aggregate selection not rerun here,
not claimed as new evidence. This is a test-fixture correction, not an archive
feature or production authorization fix.

Final expanded:191passed1failed61.32s,0skipped. Of original190:189passed/1failed;
two new boundary tests pass. Only failure:
 tests/test_track_history.py::test_real_hfacs_and_report_optional_extension_three_generations
503HFACS_CORE_UNAVAILABLE in run_core(taxonomy), same failure retained from baseline.
Targeted4overlaps this expanded set; counts not additive. No claim entire suite passes.
Local logs:/tmp/mcis-supported-workflow-targeted.txt and
/tmp/mcis-supported-workflow-expanded.txt; digests stored alongside.

# Supported ordinary archive workflows on PR104 — developer review

## Exact dependency and test intent
PR104/e56458165df0ac219f75a0778b989ffb005dd702 and main94d5e38 were reread unchanged.
Existing test-only candidate b89d3fdd4b5bcf48f5f95890b9de4b2c75bfb27c has direct
parent88cc9fd, the earlier PR104 aggregate. The current report repair chain and
b89d3fd overlap only in REQUESTS/ROADMAP append-only documentation. In this isolated
local worktree both complete additions were retained; all four test files match
b89d3fd exactly. Product source, web, contracts and permissions match e564581.

The metadata test checks five editable fields, immutable/other-record preservation,
full before/after audit and supported case restoration. The vessel test checks
creation, supplied source/parameter values, operator attribution and archive vessel
content. Neither requires unrelated histories from the complex seeded demo.

Existing W8.4 contract, section '既有案件包标准化边界（D01裁定）', explicitly permits
missing legacy fields to normalize and revision to change. The isolated fixture
POST-creates a new synthetic case with explicit legacy fields to test a stable
supported representation. It does not promise arbitrary sparse records preserve
revision or change production serialization. No existing demo data are deleted.

Original assertion ASTs: metadata13/13 and vessel7/7 retained. New totals16/15 add
status/list validation, audit-chain verification, real vessel import/re-export.
Only these two tests select the new fixture. Editing still uses its original role;
full audit/export/import use explicit authorized LeadInvestigator. Other fixtures
and all production authorization rules are unchanged.

Separate ordinary synthetic boundary tests retain default-role403 and explicit
Lead409 ARCHIVE_RESTORE_UNSUPPORTED for the untouched complex seed. They assert
JSON/noZIP/noattachment plus unchanged temporary DB rows and file hashes. This is
not support for complex cases or a removal of unsupported state.

## Baseline rerun
Original two functions on the unchanged e564581 service tree were rerun from the
report worktree (HEAD596d218 adds only frontend acceptance documentation):

    ./.venv/bin/pytest -q tests/test_case_metadata_w84.py::test_read_update_audit_original_and_roundtrip tests/test_vessel_entry_w91.py::test_create_reopen_export_and_audit

2 failed in0.99s: default audit denial parsed as a list causes TypeError / KeyError.
This does not itself reach export409. The integrated boundary test independently
checks the existing Lead409 behavior rather than weakening it to make the flow pass.

## Candidate ordinary regression
From service/:

    ./.venv/bin/pytest -q tests/test_contracts.py tests/test_case_metadata_w84.py tests/test_environment_w92.py tests/test_track_history.py tests/test_vessel_entry_w91.py tests/test_archive_workflow_boundary.py --deselect=tests/test_track_history.py::test_real_hfacs_and_report_optional_extension_three_generations -rs

The explicitly deselected HFACS test is NOT executed, repaired, mocked or counted
as passing. The original190 group plus2 new boundary tests contains192 items;
191 are selected. This is ordinary synthetic product/temporary-storage verification,
not real cases, actual original evidence, production identity or browser testing.
Historical b89d3fd report's191pass/1HFACSfail is prior evidence, not a run this turn.

Final result: **191 passed, 1 deselected in62.64s**, no selected failures or skips.
Of the original190,189 ran and passed; the excluded real HFACS test remains unverified.
The other2 passes are the added boundary cases. Counts overlap previous runs and
are not additive. No restricted historical-report integrity/ECFC operations retried.

## Conclusion and limits
The test isolation is appropriate for the stated workflow and can be submitted for
independent review. It does not repair or enable unsupported complex archives,
authenticate client role headers, fix normalization, or solve HFACS dependencies.
No source or test assertions were weakened. Existing report fixes remain intact.
This local integration was not pushed, applied to PR104, merged into main or deployed.
No browser/production/CI acceptance, no full-system claim. Prior files are preserved
as historical records, with this result describing the new exact combined tree.

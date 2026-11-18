# Exact PR96 + PR102 integration — developer verification

Fresh complete worktree from current remote main:
94d5e38c926fda232bb987b60fa9145e4bcf01a7.
PR96 OPEN head3afd139423ddcd3ef028247d3d97982b46da4026, base main.
PR102 OPEN heada400fa9bf43cc7e686295d2f28823530d22a333a, base main.
Both heads directly parent that exact main; neither is merged/patch-equivalent
on main (git cherry +). Queried all52open PR file lists: no other open PR overlaps
these functional/test paths, excluding REQUESTS/ROADMAP. No replacement found by
this source/file-scope check; does not establish semantic equivalence of all PRs.
Final read of main and both remote source branches unchanged.

Branch integration/pr96-pr102-main. First merge b0e5e12 includes exactPR96;
second merge63461fbc6ee9d5f1ef84b02b4dbd5caa47c5775d includes exactPR102.
No long research branch inherited. Only REQUESTS.md and ROADMAP.md conflicted:
both were proven base-prefix-plus-append, resolved base+PR96append+PR102append.
Every other changed file byte-compared equal to its exact source PR. Both original
freeze manifests fully pass.16changed paths before this integration report.
Production permissions/routes unchanged. Only runtime addition is the opt-in
trajectory validation module fromPR102; no current adapter/network/DB integration.
PR96 only adjusts ordinary report test principals and retains denial assertions.

## Actual commands and outcomes

From service, shared pre-existing .venv symlink; no dependency installation:

    ./.venv/bin/pytest -q tests/test_reports_w16_direct.py tests/test_reports_w161_snapshot.py tests/test_shared_trajectory.py tests/test_tracks_import_w102.py

184passed40.70s;0skips. Includes69ordinary report/snapshot and115trajectory/import.
These use synthetic data and real handlers/temporarySQLite, not real AIS/models,
production identity, browser, or independently performed acceptance.

    ./.venv/bin/pytest -q tests/test_contracts.py tests/test_case_metadata_w84.py tests/test_environment_w92.py tests/test_track_history.py tests/test_vessel_entry_w91.py

187passed3failed67.00s;0skips. Exact failed node IDs:

- tests/test_case_metadata_w84.py::test_read_update_audit_original_and_roundtrip
- tests/test_track_history.py::test_real_hfacs_and_report_optional_extension_three_generations
- tests/test_vessel_entry_w91.py::test_create_reopen_export_and_audit

Separate clean detached baseline worktree at94d5e38, run those exact3node IDs:
3failed1.57s, identicalIDs and failure classes. First/third do not check audit
HTTP status before treating error-object as list: TypeError and KeyError('events').
Earlier independent diagnosis associates these with default Investigator audit
policy; this run preserved the actual failures and did not change roles/policies.
Middle fails503HFACS_CORE_UNAVAILABLE in run_core(taxonomy). Launcher exists;
no dotnet onPATH and no generated HFACS DLL observed. Did not install dependencies,
substitute core output, add skips, or modify protections to make tests pass.
Core attempted build generated untracked out/ artifacts, not committed.

## Limits and disposition

Local ordinary integration verification only, not full-system acceptance.
No frontend changes, frontend build/browser not run. No real AIS, Unity adapter,
LLM, authentication, or true HFACS result verified. No previously restricted
historical integrity/security/ECFC suites retried; no protection-setting queries.
No production deployment/main merge/forcepush/PR closure. Both existing PRs remain
open. Local integration branch awaits independent review; no push in this task.

Raw local outputs (not required for code checkout):
/tmp/mcis-pr96-pr102-focused.txt, /tmp/mcis-pr96-pr102-related.txt,
/tmp/mcis-pr96-pr102-baseline.txt. Their SHA256 values are stored alongside this
report; raw fixture/error dumps not added to Git. Existing historical reports in
PR96 remain byte-identical and retain their original dates/test scope.

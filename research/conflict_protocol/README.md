# Developer-only conflict retention / case protocol control

Parent 4bab226c3d05464d86337e5e0ff4bff9f6b9123f. Adds only this directory; original scorer and fixture remain untouched. No model, OCR, external call, product policy or human authority. Repository guidance previously read remains applicable; this is a separately authorized research candidate, not a contract change.

## Run
From a checkout of this candidate:

    python -I -B research/conflict_protocol/check.py

For an exported candidate, explicitly supply --score-root /path/to/report_extraction_four_metrics and --dependency-root /path/to/pinned-export. That exported mode was actually executed: 7 tests, exit 0. Full-checkout invocation was not executed in this environment. The original scorer SHA-256 is checked as 11b1b98fd925adda8228489d842e2a766b04b85d1f2d5aa86bd24832cdef77ec. Its dependency manifest is also hash checked; the reused UTF-8 locator blob is verified before loading. No dependencies are copied into this candidate.

## Frozen control, not output-selected policy
manifest.json was created before the verifier and contains a new visible synthetic three-line source: two incompatible observer statements and an explicit unresolved qualifier. Its fixed SHA-256 is 5d34c0053abb164f2981c08c7f4802d30d7a22bc3913b7a3da44d05ec18944a3. The required item universe, conflict group and allowed unresolved status are read from that pinned manifest, never from extraction output. Output cannot supply a policy. Developer review records are bound to both manifest hash and complete output digest; those bindings do not authenticate a reviewer.

## Observed protocol distinctions
- Both sides plus qualifier and unresolved disposition: developer_control_pass only, not an approved real case.
- Both sides plus qualifier but explicit invented observer_a_confirmed disposition: actual unchanged scorer yields conflictRetention=1/1; protocol fails invented_resolution.
- Both sides, qualifier omitted, completed developer review: conflictRetention=1/1 and recall=2/3; protocol fails confirmed_missing_unresolved_qualifier. That status means the synthetic review has completed, not that a human really reviewed it.
- Same missing qualifier while review is incomplete: pending_human_decision, pendingMandatory=[unresolved], no confirmed omission and no final recall/conflict metric. Elapsed time is not review completion.

Additional tests reject manifest edits, stale output-review bindings and output-supplied policy, and verify no mutation. No hidden data or independent reviewer answers are loaded. result.json and tests.log are actual execution evidence, not a model score.

## Limits
The resolution is an explicit structured control field, not a detected natural-language conclusion. S labels and matches are handwritten developer controls. This cannot detect invented resolutions buried in unrestricted prose or authenticate completeness/independence of review. Future actual extraction needs independently established proposition matching and semantic assessment. Conflict retention counts preservation of sides, not resolution, source weight or a case-pass decision. Existing OCR/model readiness limits remain unchanged. No service, W20, contracts, deployment or merge.

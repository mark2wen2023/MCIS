# PR 34 integration candidate, 2026-11-13 02:30 UTC+8

Inputs: main `3aba2bf03e393909c611489ae573a887087637ac`; PR `1ad3695c4a5233ecf30a515e79a5a33bd81f92fc`; base `276fe2529432041d5d0d242bf28a7d108c44ffde`.

The recursive immutable main tree was fetched via GitHub connector. 1055 of 2229 blobs could be materialized from local files with exact Git blob SHA verification. All `service/` and `web/` blobs were available and verified. 1174 other paths (historical logs, tests, Unity, reports, images, etc.) were unavailable locally; see missing.json. This is therefore NOT a complete repository checkout.

All 26 PR paths were applied. Four overlapping paths use the earlier verified three-way candidate; the other 22 match PR-head Git blob SHA. Documentation preserves main plus PR additions, code/router merges cleanly. candidate-manifest.json records SHA256 for every applied path. Existing frozen historical test reports were kept unchanged and are not evidence for this candidate.

Allowed verification performed using existing installed dependencies, without dependency installation:
- Python API/self + independent tests explicitly excluding real_core: **88 passed, 3 deselected**. Uses temporary DBs and stubbed CPA, not real C# calculations. python-stub-tests.log.
- TypeScript `tsc -b --force`: exit 0, empty typecheck.log.
- Current-analysis self UI model/render test: passed (no browser).
- Independent UI model: 36 assertions passed, explicitly browserCoverage=false. ui-independent.log.
- main.py AST syntax valid.

No .NET command, NuGet restore, browser attempt, network workaround, remote write, commit, push, merge, or deployment was performed. Installed node_modules is a local symlink to existing dependencies and is not a repository artifact.

Remaining: independent review of the merge candidate and current-main regressions; real C# geometry tests; real browser interaction validation; exact current-main/head recheck before any remote draft save. Broad full-suite claims are not justified. Remote PR #34 is unchanged and still conflicts. A new tree can preserve all main files server-side and add these exact PR paths when an independently reviewed draft update is appropriate, but that has NOT happened.

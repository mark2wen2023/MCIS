# GitHub batch integration inventory: report + timeline archive

## Current pin and dependencies

Last remote check: main **4a6e72939c1d740707d65abb505b6eb90d585708**. It advanced during investigation from f2eff95 via #75 (exact AIS record metadata) and #76 (environment fixture correction). Earlier f2-based no-conflict and178pass/2fail results are not the latest-main acceptance. This report describes the new isolated research/aeb-main-4a6e729-integration working tree, based directly on4a6e729; no remote merge/deployment.

The published feature chain is exactly:

`f2eff95 → fe365879b33453ce03ce8aee1f62344a8b9db4e5 → aeb8cf1dfb18b2fd723a6d98112e550b83054801`.

fe36587 provides format1.4 backend/schema/contracts and tests; aeb8cf1 provides matching strict web parser/scope text. The web commit depends on that backend. Treat these two as one functional batch for final review; do not advertise working UI by merging only the backend or claim backend1.4 support from the web-only diff. There is no97-commit dependency stack. Report+recommendation research is separate and must not be included as working functionality.

## Conflicts and local composition

`git merge-tree --write-tree 4a6e729 aeb8cf1` reports only REQUESTS.md and ROADMAP.md append conflicts (original-conflicts.json). All other feature patches apply cleanly. A new worktree on4a6e729 received the aeb-relative-to-f2 patch excluding those two files; both files were resolved as exact latest-main text followed by the feature's append-only suffix. No main ref, remote branch or protection was modified; no git merge command/merge commit was made.

Independent byte checks prove all13 feature service/web/contracts paths equal aeb, while cases/service.py and test_environment_w92.py exactly retain latest main #75/#76. REQUESTS/ROADMAP retain both histories. Machine records: tree-check.json, independent-hashes.json; final hashes logs/aeb-main-integration-hashes.txt. This local composition is a review candidate, not authorization to merge. Any further main advance requires another conflict/test assessment.

## Actual current-combination verification

Coordinator fresh combined command:

```sh
PYTHONPATH=service service/.venv/bin/python -m pytest -q \
 service/tests/test_report_timeline_archive.py \
 tests_acceptance/report-timeline-independent/test_boundaries.py \
 service/tests/test_working_record_archive.py \
 service/tests/test_package_intake_parser.py service/tests/test_package_intake_router.py \
 service/tests/test_archive_export_safety.py service/tests/test_track_history.py \
 service/tests/test_environment_w92.py \
 tests_acceptance/EXACT_SAMPLE/test_exact_sample.py tests_acceptance/EXACT_SAMPLE/test_independent.py \
 tests_acceptance/aeb-main-integration/test_mixed_history.py
```

**263 passed, 2 failed /88.05s** (backend.txt). The two nodes are the actual HFACS-dependent working-record and track-history workflows. A newly created, unmodified detached4a6e729 control worktree independently from the candidate composition reproduces **the same2 failures /1.50s**, HFACS_CORE_UNAVAILABLE (current-main-control.txt). This is a current-main node control, not a green full-main suite. No .NET installation/core substitution/skipping was used.

Independent reviewer: **107 passed /39.91s** (26 feature+7 independent boundaries+70 environment+4 independent exact-sample), plus exact source/docs-preservation checks; see independent.md. Its initial collection error due to bare sibling imports was retained; correcting PYTHONPATH to include tests_acceptance/EXACT_SAMPLE produced the successful run without changing assertions/product. The reviewer did not claim to rerun the263-case broad scope.

Additional real API test creates valid CSV track-import history, report and timeline, then verifies excluded combination export409 with full SQL snapshot and original bytes unchanged. It passes in the combined run; before main update it also passed independently. This tests real mixed state, not just a forged version number.

Real ASGI service in current tree:1.4 preview200/commit200/GET receipt200 and exact timeline rows; Investigator403; mismatched track version422/zero cases. Actual response JSON passes frontend parse/receipt binding and React SSR (api.txt/ui-responses.txt). Build passes with existing large-chunk warning (build.txt). Synthetic data only. These are not browser interactions or production identity proofs.

## Browser evidence and release blockers

Current-combination sandbox-enabled launch attempted again: Chromium156.0.8078.79, `chromium_sandbox=True`. Browser aborts before page creation because SUID sandbox helper is owned by nobody rather than root (mode4755). Full evidence browser-sandbox.txt. No plugin installed, no sandbox disabled, no elevated permission/helper change. This is an environment blocker, not an approval-review rejection. URL/render/console/click/checkbox/receipt/reload/mobile/screenshot behavior remains unvalidated in a real browser.

Do not merge this batch as fully validated yet:

1. Real browser1.4 select→preview→explicit-confirm→receipt/entered-case flow, denied scope and uncertain-write/no-auto-retry need sandbox-capable independent verification. SSR is insufficient.
2. HFACS-dependent combinations remain unavailable; two actual current-main baseline failures are preserved, not silently relabeled passes. If the release claims those optional workflows, provision the real core and run them.
3. GitHub required checks, branch protection/review approvals and deployment readiness are not certified by local merge-tree or test results. This task did not create a PR, request bypasses, merge or deploy. Only coordinator/authorized review should advance the batch after required gates pass.

Scope remains bounded1.4 report/work-record + timeline. Track+timeline, recommendation, consultation, conflict, COLREG and agent/unknown states remain refused. Self-reported roles, long write locks, archive memory bounds, historical claims and DB/filesystem crash/uncertain-commit limits are unchanged. No production performance, SSO or whole-service test success claim.

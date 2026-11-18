# PR96 / PR98 / PR102 integration candidate

Parent preserved exactly:141eb503eae0acfe02f050cc4a30806b2a53b24c
(branch integration/pr96-pr102-main, remote unchanged).
New branch:integration/pr96-pr98-pr102; merge4fd400f includes exact PR98 head
51c9418b3a1f12a52042c0bf1761dd9c57abd9ca.
PR98 directly parents current main94d5e38c926fda232bb987b60fa9145e4bcf01a7.
PR96 3afd139423ddcd3ef028247d3d97982b46da4026 and PR102
a400fa9bf43cc7e686295d2f28823530d22a333a remain ancestors through parent141eb50.
No preceding research-stack or new feature code introduced.

## Difference/compatibility

PR98 changes only AlignPreviewPanel's add-source updater, model's first-unused
SOURCE-n allocator (four-source cap), associated synthetic test and freeze log,
plus workflow appends. No runtime overlap with PR96 test-fixture correction or
PR102 opt-in Python trajectory contract. Source text/mappings and existing IDs
are preserved, duplicate declarations still rejected. This is temporary CSV
labelling, not identity inference or a shared-trajectory adapter.

Only REQUESTS.md/ROADMAP.md append conflicts. Resolved existing141eb50bytes plus
PR98's exact addition beyond its main base. All three PRs' other files compare
byte-identical to their exact heads. All3freeze manifests pass. Parent report
and existing appended progress remain unchanged. No permission/backend changes.

## Developer validation actually run

From web using pre-existing shared node_modules; no installation:

    bash tests/run-align-preview-w41.sh
    ./node_modules/.bin/esbuild tests/align-source-numbering.test.ts --bundle --platform=node --format=cjs --outfile=/tmp/mcis-combined-source-numbering.cjs --log-level=warning
    node /tmp/mcis-combined-source-numbering.cjs
    npm run build

32 model/static-render checks passed. New numbering suite passed (source test
reports no numeric assertion total). TypeScript/Vite8.3.8 build passed,766modules,
1,856.36kB JS; existing >1500kB chunk warning. This is the new combined source tree,
not the earlier isolated PR build. No true browser or clean-install/CI validation.

From service using pre-existing shared .venv:

    ./.venv/bin/pytest -q tests/test_reports_w16_direct.py tests/test_reports_w161_snapshot.py tests/test_shared_trajectory.py tests/test_tracks_import_w102.py

184passed35.95s;0skips. Synthetic cases/ordinary functions, not production identity.

    ./.venv/bin/pytest -q -rs tests/test_align_preview_w41.py

29passed1skipped8.69s. Existing test_real_cli_csv_preview skip at line66:
'real CLI SDK required'. The29 ordinary adapter tests use explicitly mocked core
results/failures; they do NOT prove .NET alignment, real AIS, or model execution.
No new skip/xfail added. The skipped test is not a pass.

## Retained limits

Parent141eb50 related group:187/190passed,3failed, and exact main rerun of same3
failed identically. That group was not rerun this turn (PR98 adds no backend
change); failures remain unresolved. See parent integration report for exact
commands/node IDs: two audit-response assumptions and HFACS_CORE_UNAVAILABLE.
No claim of full repository, real HFACS, AIS/LLM, browser, SSO, deployment or
independent combined acceptance. No previously blocked browser/security/ECFC
operations retried. Main/original integration branch/PR98 remote heads reread
unchanged; no PR closed, no main merge/forcepush/deploy. Local candidate only.

Local outputs: /tmp/mcis-pr96-pr98-pr102-focused.txt and
/tmp/mcis-pr96-pr98-pr102-align.txt; SHA256 recorded alongside. Frontend output
was observed directly in tool results; no separate raw browser/build log claimed.

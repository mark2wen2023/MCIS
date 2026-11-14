> 历史证据归档（2026-11-14），不是当前授权或可执行说明。未在本次归档重跑原测试/模型；旧raw-key路径已在498f807禁用，真实执行仍HOLD。来源、原始摘要和归档摘要见MANIFEST.json。

# MCIS PR integration audit — 2026-11-14

Read-only remote audit; local simulations only. No remote writes, PR updates, merge commits, deployment, model calls or public listeners. Original implementation checkout remains unchanged. Evidence is local in this directory.

## Exact snapshots

| PR | Head | Actual target |
|---|---|---|
|57|2104fcbeef2d1fd296b046fbf44a972c43c351e1|research/sk-t01-preview-20261113|
|58|0b005fe7043b90d48929cb3eced2fc587c60443b|research/sk-t01-preview-20261113|
|61|aad96d439d34d112cd07637fc341c06dbaf22978|research/sk-t01-preview-20261113|
|64|5d10b67db47e55b6352b559ec1d00ae61ede99c7|research/sk-t01-preview-20261113|
|67|5069ba384d9f728df5421e56fad763dde6eabd91|main|

Main is 3aba2bf03e393909c611489ae573a887087637ac. PR56 head is 254167e3e957784fd9d2d136a275731f33314d9b, 97 commits / 566 changed files beyond main. All five are open drafts at inspection. Do not simply retarget 57/58/61/64 to main: their ancestry includes those 97 commits, regardless of a small PR diff against PR56.

## Simulations and conflict evidence

1. Fresh isolated clone `/workspace/mcis-integration-audit-20261114`, detached at PR56. Applied exact base-to-head patches in order 57,58,61,64,67 with `git apply --3way`. No implementation conflicts. Every later patch conflicts only in shared append-only REQUESTS.md and ROADMAP.md; local `git merge-file --union` retained both additions. No merge commit was created. See integration-apply.json and integrated-diff-numstat.txt.
2. Separate `/workspace/mcis-main-patch-probe-20261114`, detached at main. Every implementation patch passes direct `git apply --check` when excluding those two workflow documents. Applied all five deltas locally, without PR56 ancestors. This is an extraction experiment, not proof that retargeting the original branches is safe.
3. PR57 cannot run on that main-only extraction: collection fails because `export_review` is missing. Its renderers require PR56's export_review.py, render_review.py and evaluate.py plus their data/contracts/tests. Textual applicability is not runtime independence.
4. On main-only extraction, PR58/61/64/67 combined focused backend/acceptance suite passes 193 tests, and full web TypeScript/Vite build passes (chunk-size warning only). This supports creating main-based extraction candidates with renewed acceptance, rather than dragging all PR56 history into main. It is not an isolated proof for each PR separately.
5. Full PR56+five-PR web build fails TS6133 unused React imports in evidenceQuote/SourceQuoteReview.tsx, extractionReview/ExtractionReview.tsx, extractionWorking/ExtractionWorking.tsx and workingArchive/WorkingArchive.tsx. A fresh unmodified PR56 web+contracts snapshot, same dependencies, reproduces the exact four errors. These are baseline blockers, not introduced by the five deltas. No fix was made during this audit.

## Validation

- Combined PR56+five-PR targeted Python suite: 229 passed (193 service/independent cases plus 36 semantic harness cases). Semantic harness rerun: 36 passed; it generates the HTML and invokes the Node adapters with required arguments.
- Combined service-only repeat: **193 passed, exit 0**. Broader report-output/access/recommendation/intake/archive regressions: **342 passed, 1 skipped**, exit 0. The skipped case is `test_intake_csharp_custody_compatibility`: existing .NET SDK required; confirmed separately with `-rs`.
- W75 primary UI: 20 DOM checks +6 malformed-response checks. Independent UI: 20 checks.
- Restored filename primary transport/parser: 23 checks; independent: 14 checks. Synthetic fetch, not a real browser download.
- Both integration scenarios use fresh source directories and existing service venv executables; PYTHONPATH explicitly points to each tested checkout. npm ci in the integration directory succeeded. No source changes were made to make tests pass.
- Initial ordinary pytest collection collided on repeated test_independent.py basenames; final commands use `--import-mode=importlib` plus PYTHONPATH=service:. Initial importlib invocation without PYTHONPATH also failed. Raw logs retained, not counted as passes.
- An initial bare `node --test` attempt failed because these files require generated HTML arguments; use the passing Python harness instead. Initial UI invocation lacked optional happy-dom; explicit existing `/tmp/mcis-ui-deps` path fixes the environment without dependency/lock changes.

## Browser and identity gaps

Sandbox-enabled Playwright Chromium launch (`chromiumSandbox:true`, `/usr/bin/chromium`) failed before navigation: SUID helper not configured and crashpad errors. No no-sandbox retry, permission mutation or server startup was used. Raw browser-sandbox-probe.txt retained. Old repository browser scripts that hardcode --no-sandbox were deliberately not run. No actual browser or filesystem download acceptance is claimed.

common/context.py:1,27-32 explicitly trusts X-MCIS-Role (default Investigator) and X-MCIS-Operator. web/src/api.ts and recommendationEdit/BodyEditor.tsx send localStorage identities. Thus 61/64/67 enforce the current local role policy, not authenticated users. The separate identity HTTP trial is deliberately unmounted from legacy create_app; its existence does not authenticate these endpoints.

PR57 is an offline research worksheet, not the mounted workbench, and does not authenticate authors. PR58 plans are executable:false: no intranet connection or production credential/session integration. PR64 applies full-content policy to recognized ZIP bytes in both active download routes; it is not general DLP and does not cover arbitrary text/PDF re-encoding. PR61 restores names/bindings, not content authenticity.

## Recommended sequence (requires separate authorization for future writes)

1. Preserve current heads and evidence. Do not integrate all PR56 merely to deliver these four small operational changes.
2. Prepare main-based extraction candidates for PR64 (ZIP permission hardening) then PR61 (restore naming). Their implementation files do not overlap; this ordering closes the known content-access gap before UX metadata completion. Re-run report ZIP generate → explicit intake → case export → restored historical download, both authorized and denied roles, checking original bytes/name and audit.
3. PR67 already targets main; integrate only after current client/backend 428 and version conflict behavior, full history and cancellation tests are accepted. It is independent of 61/64. PR58 is another independent main-based extraction candidate, explicitly kept offline; it can proceed alongside 67. Re-freeze contracts/workflow docs and run final combined checks on the chosen actual integration candidate.
4. Keep PR57 stacked on PR56 for now. Either review PR56's 97-commit dependency chain and fix its four baseline build failures, or separately extract the minimal research export/evaluation dependency closure and revalidate. Do not pretend a simple retarget solves its missing imports.
5. Before declaring formal release-ready UI: run supported sandbox browser tests for file import/export, native attachment download/name/bytes, cancel/duplicate/race behavior, recommendation save-unknown states, and identity/case changes. Capture real artifacts.
6. Before production authenticated deployment: bind server sessions to real subjects and case membership; reject forged role headers/localStorage, missing/expired/revoked sessions and cross-case requests, including all legacy read/download bypass paths and revocation during writes. This is a separate prerequisite, not supplied by any of these five PRs.

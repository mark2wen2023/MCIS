# Evidence registration failure feedback — QA report

Base3aba2bf, isolated branch local/evidence-failure-feedback. Only evidenceIntake API/UI error handling and a focused test changed; server/default identity/archives untouched. No push/deploy/merge, no retry/delete implementation.

## Actual defect and fix

Old save handler cleared original preview/body and unlocked on almost every4xx, including INTAKE_INTEGRITY409. Real server load_receipt emits that code when an existing registration's source bytes/binding fail verification. Thus4xx does not prove absence of a previous registration. Another potential state-machine defect was clearing an earlier unknown outcome after a later denied attempt.

New classifier permits re-preview only for exact known pre-registration code/status pairs and only without earlier uncertainty. Fourteen code locations inspected; these indicate this invocation was rejected before registration, not that historical same-content registration is absent. Other409/network/unparseable response/500 stay locked. Unknown state is not cleared by later rejection. Remove manual retry button from uncertain panel and stop recommending retry after recovery404; only read-only recovery remains. Close/navigation behavior remains unchanged and clears in-memory state: no cross-reload lock or persisted recovery guarantee is claimed.

Current evidence endpoint does NOT return a generic X-MCIS-Write-Outcome header on main. That header belongs to knowledge archive in this baseline, and was not borrowed. No HTTP status alone is interpreted as global not-committed proof. Server500 INTAKE_CLEANUP_FAILED remains unknown regardless of its optimistic body text. Server cleanup/commit-ambiguity behavior is NOT fixed here.

## Environment and reproduction

Browser plugin not available; used existing Python Playwright + /usr/bin/chromium, no dependency installation. Actual app at127.0.0.1:15942, actual synthetic Uvicorn API127.0.0.1:18942, fresh temporary SQLite/files, viewport1440x1000. Test flow: evidence workbench -> select synthetic file -> real preview -> confirm registration failure -> retained original request and read-only recovery.

ProbeA: independently register exact preview via actual HTTP, locally overwrite its source.bin (explicit local modification capability), then click UI commit. Real server409 INTAKE_INTEGRITY. Before patch title field unlocked and preview cleared; after patch title remains disabled, original preview retained and no retry button. Recovery409 keeps locked. Exactly one browser commit and one Register in each probe; no remote-write exploit claimed.

ProbeB: normal UI request genuinely commits200 through route.fetch, then test transport intentionally drops that response. UI stays locked/unknown; actual read-only GET recovers verified receipt. Exactly one commit/one Register for that case. This is a controlled lost-response fault with real backend success, not a fake successful API response.

## Checks and results

| Check | Result |
|---|---|
| Page identity/nonblank | PASS, MCIS investigation workbench/evidence route |
| Framework overlay/page exceptions | PASS, no overlay or pageerror |
| Console | Collected in after.json; expected HTTP409 and injected network failure; one additional404 without URL in console capture remains unattributed (not claimed console-clean); no service404 in saved log |
| Screenshot/interaction | before.png, after.png, unknown.png; disabled field, preserved digest, recovery-only control verified |
| TypeScript | tsc -b --force passed |
| Targeted lint | oxlint changed source/test passed |
| Existing model/API/render |88 assertions passed |
| New classifier |19 synthetic assertions passed |
| Service regression |84 passed1 skipped17.52s; skipped existing.NET SDK check |
| Independent |80 classification assertions;5 real service/SQLite probes passed1.94s; no separate independent browser run |

Independent checks include all14 code/status combinations, mismatched status/case, previous-unknown invariant, exact errors and server existing-registration integrity conflict preserving database1/1/1. Counts describe different suites, not a combined unique coverage metric.

## Deliverables / remaining risk

Changes: web/src/evidenceIntake/{api.ts,EvidenceIntakePanel.tsx}, web/tests/evidence-intake-outcomes.test.ts. Browser reproduction script and all synthetic results/screenshots in this directory; separate independent report under independent/. Local patch generated separately. No mobile/cross-browser validation; no production identity, durability, global retries or storage cleanup solved. Do not call this full evidence commit atomicity repair. Prior full-suite failures remain outside targeted run.

Reproduce source tests: bash web/tests/run-evidence-intake-w42.sh; bundle/run evidence-intake-outcomes.test.ts via esbuild; service pytest tests/test_evidence_intake_w42.py. Browser: EXPECT_FIXED=1 python browser.py (absolute ROOT points at isolated worktree, change when reproducing elsewhere; all servers localhost).

## Final review packaging

Final branch codex/evidence-failure-feedback-review is based on3952a03, retaining that parent fix. See DEPENDENCIES.md for exact hashes, PR69 conflict simulation and final-parent Chromium rerun. The earlier base3aba reference above describes original reproduction. Final source hashes are unchanged. Browser script now derives repository root and accepts MCIS_QA_OUT; independent classifier imports are repo-relative for cross-environment review. Final-parent source tests88+19 and independent classifier80 rerun passed; independent backend5 rerun passed. Prior service84/1skip remains same-source regression evidence, not a second full service run.

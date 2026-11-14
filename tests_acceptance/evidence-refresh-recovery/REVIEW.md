# Review packaging and reproducible environment

Direct parent d1a442474aed81265227b24014516facc2bbbc6c verified against remote codex/evidence-failure-feedback-review before push. Its parent3952a032a3e61d59d75d1569a449983d0e276606 is retained, and3952a03's parent is main3aba2bf03e393909c611489ae573a887087637ac. New branch codex/evidence-refresh-recovery-review adds only this refresh-recovery slice. No PR69 implementation or98-commit dependency stack is introduced. PR69/source integration simulation belongs to the parent review; it was not rerun as a full combined browser task here.

Product diff: existing EvidenceIntakePanel uses new pending.ts helper; new pending test plus review/docs/freeze. No server, default identity, archives, model calls, cleanup or automatic resend changes. Frozen hashes verified before packaging. Review artifacts contain synthetic cases/bytes and tests only. No runtime database, node_modules, virtualenv, generated bundles or .env included.

## Actual environment

Recorded via local commands in environment.json, not inferred from package ranges:
- /usr/bin/chromium:156.0.8078.79, Debian13 build.
- Playwright1.62.0, system driver Python3.12.14.
- Node24.22.1; Vite8.3.8.
- Existing service virtualenv Uvicorn0.54.0/FastAPI0.162.7.
Browser plugin unavailable: regular installed Playwright used; no dependency installation. Script calls chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox']). This flag is a recorded container-browser launch setting, not a production configuration or authorization bypass. Script records actual launched browser.version in after.json.

## Startup and exact test

Run from repository root with existing service/.venv and web/node_modules:

```sh
MCIS_QA_OUT=/tmp/mcis-refresh-review python tests_acceptance/evidence-refresh-recovery/browser.py
```

Use a Python interpreter with Playwright installed; here system `python` supplies it, service/.venv does not. Script creates fresh temporary MCIS_DATA_DIR and disables model URL/model values for child processes. It imports existing web/tests/evidence-intake-w42.fixture.py to create synthetic cases, launches service/.venv/bin/python with uvicorn.run(app,host='127.0.0.1',port=18942), then Node Vite with --host127.0.0.1 --port15942 --strictPort. Both bind localhost. It waits for service health and UI, launches Chromium1440x1000, exercises real endpoints, records evidence and terminates its own server process groups in finally. Port conflicts fail startup; choose/edit both ports explicitly rather than connect to unrelated processes.

FlowA retains parent actual409 integrity scenario. FlowB genuinely commits200 then deliberately aborts response delivery, reloads, checks only four fields persisted, and no file/statement restored. A deliberately injected GET404 retains lock. Actual server policy is then revoked using authorized synthetic LeadInvestigator PUT, producing real403 and keeping marker. Policy restored, real GET recovers matching receipt and clears marker. Exactly one commit and Register for that case. No successful API response fabricated. Returned source/audit evidence is synthetic; this is not SSO or production-case validation.

Console includes expected409, injected network failure/404 and actual403 plus one unattributed initial404; no pageerror or framework overlay. Desktop-only. refresh-404.png name is historical: final screenshot is taken after subsequent403, with marker and lock still visible. Marker display is not a server success receipt.

## Tests and limits

Final source model/API/render88 passed; pending-storage test passed; independent60 assertions rerun passed; TypeScript and targeted lint passed. Prior service84passed1.NETskip is parent evidence only; backend not changed and not rerun in this slice. Browser evidence rerun from this exact worktree before commit, final code freeze checked. No claim of cross-tab/device protection, durable browser storage, crash-safe server commits or real identity. No files or unknown server objects deleted. Same-session marker false positives (crash before network dispatch) intentionally require manual investigation.

No merge/deployment/PR creation. Push only authorized independent branch, no force push.

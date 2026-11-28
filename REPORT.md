# W11 existing ECFC editor: real save, restart and reopen (Grokbot independent acceptance)

- Product baseline: `875ccc50b049fb24b82f6b0663f3f9476db1880e` (no product, identity, permission, contract, main, CI or 3D change).
- Acceptance candidate: `candidate/w11-ecfc-real-save-acceptance` @ `21a90fb6fbbd65b083ed3c9fb5ca0af0089e0f6b`; diff vs baseline adds only `tests_acceptance/w11-ecfc-real-save/{server.py,run.py}` (+141 lines).
- Reuse check: `tests_acceptance/ECFCNEW/browser_real.py` exists at the same commit but launches Chromium with `--no-sandbox`, never completed (logs/ECFCNEW-verification.md records 0 UI assertions) and has no service restart, so it was not reused. Its `server.py` re-seeds on every start, so a seed-once server was added.
- Command (from the candidate root, 150 s external timeout):
  `W11_SAVE_OUT=<out> W11_SERVICE_PYTHON=/workspace/mcis-w17-871db66/service/.venv/bin/python MCIS_DOTNET=~/.dotnet/dotnet timeout --signal=TERM --kill-after=10s 150s <existing python-playwright venv>/bin/python tests_acceptance/w11-ecfc-real-save/run.py`
- Result: **exit=0, 17/17 checks** (accept-out/stdout.json, receipt.json, exit.txt).

## Chain
Real Chrome 156.0.8078.47, headless, `chromium_sandbox=True` (no `--no-sandbox`) → existing Vite dev server (127.0.0.1, proxy /api) → existing EcfcPage at `#/ecfc?case=W11-REAL-SAVE-FICTIONAL` → real FastAPI `create_app` on 127.0.0.1 → real C# CLI `tools/mcis-ecfc` (existing .NET SDK 8.0.428, offline local build; out/build-manifest.json sha256 d8ebeb40…, mcis-ecfc.dll f548818b…) → temporary SQLite. No API doubles; browser routes only abort non-loopback requests (0 blocked). Role/operator use the existing localStorage self-report (LeadInvestigator / "Synthetic W11 Save").

## Steps and checks
1. Fictional case seeded once: N1 Event "Fictional vessel alters course" (primary candidate), N2 Condition "Fictional restricted visibility", E1 N2→N1, one synthetic source EV-901.
2. Preview via the existing button: heading 结构已接受; SQLite (drafts, audit, requests) = (0,0,0) → **zero write**. Screenshot 01.
3. Archive acknowledgement checked, one explicit click on 保存 ECFC 人工草稿: receipt verified in page; counts (1,1,1). Screenshot 02.
4. Service terminated (exit -15) and restarted as a new process on the same port and the **same SQLite** (db sha256 between runs 352a9bb2…).
5. New browser context reopens the page: status 已读取保存版本 1; GET draft before vs after restart has identical revision (1), digest, draft (scope, nodes, edges, time, lanes) and sources; form fields show the saved text and N2→N1; re-preview renders N1, N2 and E1 N2→N1 and stays zero-write; audit panel lists exactly 版本 1 and no 版本 2; DB audit rows = 1; save POSTs across both phases = 1. Screenshot 03.

## Disclosed observations (not judged)
- The app shell header requests the demo case `CASE-2026-DEMO-LILY-MARY` (404 ×4, seed_demo off), so the header shows 案件信息不可用 and the shell footer badge shows OFFLINE; the ECFC page itself was served normally. Console errors are only these 404s; 0 page errors.
- Vite HMR WebSocket connects same-origin to 127.0.0.1.
- Raw service log is included (synthetic only). Temporary SQLite is not included.

## Not covered
Layout, source/excerpt linking, archive/export, replay, Windows/Unity, production identity, multi-user concurrency. No CI, no merge, no deploy, no install, no model calls, no real case files.

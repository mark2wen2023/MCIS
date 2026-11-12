# W12.2 implementation verification (synthetic only; draft, not full acceptance)

Integrated baseline: `80fad29baad8e6a43a0f14d5421a91e7d2e29c63`. Archive A and W19.2 changes preserved by Git blob comparison. No W11/C# core changes, deployment or real-case writes.

## Passed on final implementation
- 263 scoped Python service tests in 40.78s: current analysis (44), original W12, public-case metadata note, W10.2 import, OpenAPI/schema, W19.2, archive export guard/package/manual interview, core finite-JSON handling. This is **not** full repository CI.
- Real C# numerical self-test independently checks equatorial WGS84/ENU geometry, static relative motion and negative TCPA. Core numbers retain six decimal places; test tolerance is 1e-6.
- TypeScript `tsc -b --force` and production build pass. Build retains existing large-bundle warning.
- New parser/SSR self-tests pass; original W12 94 assertions, COLREG18+58, W5 40, W16 148 and W19.2 preview model tests pass.
- `npm run lint` exits0 with34 warnings (33 existing source warnings plus an existing test warning); changed W12.2 files have no warnings. Earlier lint scanned generated bundles in this sparse workspace because original `.gitignore` was absent; restoring the unchanged tracked ignore file corrected the runner without editing lint rules.
- Old W12 seed remains `988e9abd3b39959864f42912d8d3454dacd7821156fd8b21268631f30f4693e3`, matching its unchanged sidecar. Referenced public report and W14 log bytes were restored from the exact repository baseline; no seed regeneration or fabricated baseline.

## Independent findings handled before freeze
- Input deletion/invalidity during core now returns409 after discarding results; permission revocation remains403.
- Core degeneration flags are checked against input relative speed outside the1e-6m/s numerical boundary band; degenerate distance fields are mutually consistent. No second CPA implementation or core edit.
- Invalid metadata gets a useful Chinese message rather than internal FORMAT/METADATA_LIMIT codes.
- Oversized JSON integers are rejected as422 for input or502 for core output, not an overflow500.
- See independent `DEFECTS/W122.md` and `tests_acceptance/W122/` for separate evidence and final scoped disposition.

## Blocked / not run successfully
Both normal and normally-approved Chromium launch attempts failed before browser interaction with `socket() failed: Operation not permitted`. The supported CUA browser could not reach the loopback test server (`ERR_CONNECTION_REFUSED`). No security settings, identity or alternative binary workaround was used. **Real-browser interaction and visual assertions completed: 0.** Browser scripts are supplied as pending tests, not evidence of a pass. UI interruption/late-result/Back/identity behavior is not certified by API or SSR tests.

The implementation remains a **draft PR** until browser acceptance can run in a supported environment. Do not merge based on these scoped tests alone. No claim of complete W12, complete Sunday milestone, formal authentication, evidence authenticity, safety or liability determination.

## Reproduction
From repository root with SDK8.0.428 configured via `MCIS_DOTNET` and dependencies installed in `service/.venv` / `web/node_modules`:

```bash
PYTHONPATH="$PWD/service" service/.venv/bin/pytest -q -p no:cacheprovider \
 service/tests/test_current_analysis_w122.py service/tests/test_analysis_w12.py \
 service/tests/test_analysis_public_case_note.py service/tests/test_tracks_import_w102.py \
 service/tests/test_contracts.py service/tests/test_knowledge_w192.py \
 service/tests/test_archive_export_safety.py service/tests/test_package.py \
 service/tests/test_manual_interviews_w52b.py service/tests/test_core_finite_json.py
cd web
npx tsc -b --force
bash tests/run-current-analysis-w122.sh
bash tests/run-analysis-w12.sh
bash tests/run-knowledge-w192.sh
npm test && npm run test:w5 && npm run test:w16
npm run build && npm run lint
```

Pending real-service browser test: `python web/tests/current-analysis-w122.browser.py` with Playwright and a permitted Chromium installation. It uses isolated synthetic SQLite and127.0.0.1 only. Do not expose the service on an external interface to bypass a runner restriction.

## Latest-main integration supplement

After draft PR creation, main advanced to `276fe2529432041d5d0d242bf28a7d108c44ffde` (W20.3). All W20.3 additions were verified against Git blob IDs and preserved, including `main.tsx`, `routes.ts`, `caseContext.ts`, new modules and shared document appendices. W12.2's 86 frozen hashes remain unchanged.

On this integrated snapshot: 102 selected current-analysis/independent/contract/W20.3 API tests pass in19.24s; W12.2 and W20.3 frontend models, independent36 assertions, TypeScript, build and standard lint pass (existing warnings remain). These102 overlap earlier suites and must not be added to the263+47 as unique coverage. Browser acceptance remains blocked with0 completed assertions. The branch is still draft and must not be merged.

# Archive1.4 frontend alignment — bounded QA, browser blocked

## Delivery and dependencies

Parent fe365879b33453ce03ce8aee1f62344a8b9db4e5 was pushed to origin/feature/report-timeline-archive-v1 after checking direct parent f2eff95, all9 frozen hashes,26-file scope, no environment/build artifacts and no credential-pattern matches. Remote ls-remote returned fe365879b33453ce03ce8aee1f62344a8b9db4e5. Its 171pass/2HFACS failures and both parent-node reproductions remain documented in parent logs; they were verified, not relabeled green.

This independent descendant branch is feature/report-timeline-web-v1. No backend implementation change. Package preview/receipt parser now accepts1.4 only with strict working-v1 summary; invalid HFACS, working-v2/track count contamination and unknown versions remain rejected. Receipt outer-version/count/source-digest bindings remain. The summary receives the actual outer version instead of inferring1.2 from working-v1. Preview, receipt and export scope explicitly limit1.4 to working records plus timeline, excluding track-import history combinations, conflicts, recommendations, consultation, COLREG and agent drafts. No new retries, role escalation or commit/control-flow change.

## Target and actual verification

Intended rendered flow: lobby → select1.4 package → upload/preview → explicit confirmation → import receipt and truthful supported scope. Browser plugin not available. Existing Python Playwright and Chromium156.0.8078.79 were used for a sandbox-enabled launch attempt; no browser dependencies installed.

Actual successful checks:

* New package-timeline-v14.test.tsx: version/summary shape/HFACS validation, mismatched receipt binding, existing1.2/1.3 compatibility and static React scope rendering assertions pass.
* real_api.py: actual FastAPI ASGI/TestClient with separate synthetic SQLite source/target;1.4 preview200,commit200,GET receipt200; exact restored timeline rows. Investigator preview403.1.3/1.4 mismatch422 leaves target empty. Saved actual responses feed frontend parsePreview/parseReceipt and React SSR successfully. These are real handlers/database operations, not browser interaction or canned API responses.
* Existing W8.3:53 assertions; W8.5 model/render/transport suite; W18.6 HFACS model/render/scope suite; track-history18 assertions all pass. Existing transport doubles remain doubles, not real browser/network acceptance.
* TypeScript `tsc -b --force` and `npm run build` pass. Vite emits a chunk-size warning; this task did not optimize or establish a baseline for bundle size.

Reproduce backend and actual-response alignment:

```sh
PYTHONPATH=service service/.venv/bin/python tests_acceptance/report-timeline-web/real_api.py
cd web
./node_modules/.bin/esbuild tests/package-timeline-v14.test.tsx --bundle --platform=node --format=cjs --outfile=/tmp/mcis-timeline-web-tests.cjs --jsx=automatic --log-level=warning
MCIS_REAL_TIMELINE_RESPONSES=/tmp/mcis-web14-qa/actual-responses.json node /tmp/mcis-timeline-web-tests.cjs
bash tests/run-package-w83.sh
bash tests/run-package-intake-w85.sh
```

Synthetic archives/responses remain under /tmp/mcis-web14-qa and are not committed. Console logs copied with trailing whitespace normalized only. Test harness initial attempts required localStorage setup for SSR and ESM output for track top-level-await; final commands use correct harnesses. Export text now explicitly says both not-complete-case-backup and not-whole-system-backup, matching actual bounds and existing HFACS assertions.

## Browser blocker and QA checklist

`p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,chromium_sandbox=True)` aborts before page creation: SUID sandbox helper not configured correctly (must be root-owned4755; actual owner nobody4755). Read-only environment probe `unshare -Ur true` also fails: cannot open /proc/self/uid_map, Read-only file system. No `--no-sandbox`, sandbox permission modification or alternate insecure launch was attempted. This is an execution-environment failure, not an automatic approval rejection.

| Check | Result |
|---|---|
| Intended URL/title identity | Blocked: no browser page launched |
| Nonblank rendered application | Not validated in browser; SSR content checked only |
| Framework error overlay | Not validated |
| Browser console health | Not validated |
| Desktop/mobile screenshot | Not captured; no visual claim |
| File/confirmation/button interaction | Not validated in browser; real ASGI flow and unchanged control-flow source reviewed |
| Parser/receipt/range text/TypeScript/build | Passed within scope above |

## Remaining limits

Rendered/browser QA remains required in a sandbox-capable environment before a complete UI acceptance claim. No production SSO/real user authority, concurrent browser identity changes, browser unknown-write recovery, production performance or full-suite validation performed here. Parent archive exclusions/long-lock/memory/crash-atomicity boundaries remain. No merge/deployment. Do not infer unsupported mixed-state acceptance from frontend1.4 recognition.

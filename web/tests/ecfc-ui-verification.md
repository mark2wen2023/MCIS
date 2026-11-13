# New ECFC UI developer verification

This is new implementation on main 3aba2bf, not recovery of old W11 bytes or old tests.

Passed:
- 79 newly written structural/model/strict-JSON/render assertions (`ecfc-model.test.tsx`).
- `tsc -b --force`; Vite production build. Existing large-bundle advisory remains.
- Real Chromium against Vite with API doubles (`ecfc-browser.py`), NOT real backend acceptance: backup acknowledgement gates save, zero-write preview and professional error display, synchronous double-click sends one POST, save/reopen/edit retains unknown time as null, retry sends identical request ID and body, storage contains metadata only, reload retains lock without a POST, explicit current+audit check/abandon/fresh reread, case/identity/close late-response isolation, permission denial hides old body, storage-write failure prevents POST.
- Rendered event rectangle/condition ellipse/dashed influence arrow and 390px no outer horizontal overflow; desktop/mobile screenshots inspected in temporary test output. The test harness imports the actual global application style. Graph layout is schematic, not elapsed-time or causal proof.
- Targeted oxlint: no errors; two lifecycle/ref advisory warnings in Panel.tsx. No production identity or complete browser/platform coverage claimed.

Commands from repository root:

```sh
cd web
./node_modules/.bin/esbuild tests/ecfc-model.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-ecfc-model.cjs --jsx=automatic --log-level=warning
node tests/.tmp-ecfc-model.cjs
./node_modules/.bin/tsc -b --force
npm run build
cd ..
MCIS_BROWSER_BIN=/path/to/available/chrome-headless-shell python web/tests/ecfc-browser.py
```

Browser script uses installed Python Playwright, not service venv (which has no Playwright). It starts only an owned loopback Vite process and stops that process on exit. Independent real-service browser, source authorization and transactional acceptance are separate work.

Unknown delivery: metadata-only per-case/role/operator sessionStorage marker; request body remains memory-only. Reload loses that body, so no claim of identical retry after reload. Explicit current draft and newest50 audit reads plus user acknowledgement can abandon only local waiting, never revoke the old POST; then the view makes a fresh server read, clears preview/source selection, and requires new source acknowledgement. Old requests may still finish, and CAS determines conflicting writes. Absence from newest50 is never proof of noncommit.

Final visual pass: read frontend-testing-debugging, Browser control and React guidance. Browser skill is listed but no Browser extension `js` / `setupBrowserRuntime` tool is exposed by tool discovery; the delegated task explicitly permits ordinary browser testing. Installed Playwright/Chromium was used, with no dependency installation. The test flow is harness load → explicit graph drafting → preview/save/reopen or uncertain-response recovery → rendered state. Actual final desktop (1280×900) and mobile (390×844) screenshot pixels were inspected. Fixed a pre-freeze graph time-label/vertical-arrow overlap and bounded long ID labels; full IDs/text remain in the accessible editor and SVG title. Final nodes/edges fit the scrollable schematic region and mobile form wraps without outer overflow. Test-only switch buttons are outside the production panel. Real app route and real backend acceptance remain independent tasks.

Final protocol revision: every save and identical retry includes acknowledgeArchiveLimitation:true, supplied only after the visible backup-impact checkbox is checked. Preview does not include this field. API-double checks assert true on every save; model/tsc/build and browser suite rerun after this change.

## UI usability revision 2
Parent review identified maximum single-lane graph shrinkage: 40 nodes produced a11650-unit SVG viewBox but min-width was capped at1800px. Revised min-width to full layout width, retaining the scrollable container. This is display only, no core algorithm/protocol change. Added3 SSR assertions (total82) and actual Chromium40-node single-lane checks: width>=11650px, screen transform scale>=0.99, container scrollable, last node fully in view after horizontal scroll, no outer page horizontal overflow. Inspected left/right maximum-graph screenshots and reran entire API-double suite. Long labels remain abbreviated in graph with full content in editor/title. Archive acknowledgement remains required true. Previous freeze retained as W11-ecfc-ui-impl-hashes-frozen-v1.txt; revision2 recorded separately and in current freeze.

# W19 actual-page keyboard acceptance (browser execution pending)
Base f24ef201dc21bb5987bb89ad481b6924551ef235. Only this test directory added.
Uses actual KnowledgePage and its actual KnowledgeCard; no SSR substitute.
Reuses prior W19 Playwright page-operation approach, but intentionally does not execute
knowledge-w192-browser.py: that older harness starts services, saves data and disables
Chromium sandbox. This harness does none of those.

From candidate checkout, using installed tools only:
node tests_acceptance/W19-review-entry/run.cjs --web-deps /existing/web/node_modules --chromium /usr/bin/chromium
Optional --playwright /existing/node_modules/playwright chooses an existing module.
For build-only prerequisite:
node tests_acceptance/W19-review-entry/run.cjs --web-deps /existing/web/node_modules --check-build

Pin checks cover 11 actual imported source files, including KnowledgePage and the unchanged
visible version_binding fixture. esbuild bundle stays in memory. No listening server.
Playwright intercepts local test-origin navigation, bundle, and knowledge cards GET.
Every other request is aborted and causes failure; all non-GET methods fail.
The default Investigator demo identity comes from existing product code in a fresh context;
it is not a real account or backend authorization test.

Frozen texts are existing visible source v1/v2 from version_binding, merged with the existing
sample Content. Same synthetic card ID, Candidate status; digest computed over test content
JSON as a fixture version marker, not a service digest/registration authenticity claim.
The page first opens its normal Published empty list. Test selects Candidate via actual
page control, Tabs from heading until actual native summary, presses Enter, and verifies
the exact already-loaded quote and zero additional requests. Then the actual “重新读取”
button returns version 2: same card, new digest, closed details, old excerpt absent.
This verifies reload-driven replacement, not a general server push lifecycle.
No approval, save or archive actions clicked. Other card states unchanged.

Observed Linux results:
- --check-build: exit 0, 11 fixed source files verified and browser bundle built.
- sandboxed Chromium launch: exit 1 before page creation:
  chrome/browser/process_singleton_posix.cc:297 socket() failed: Operation not permitted.
- No keyboard, rendered-page, request-count or replacement assertions have executed here.
- No --no-sandbox, sandbox disabling, install, CI, external service or fallback browser.
Temporary Chromium profile cleanup was reported by Playwright.

Coordinator must run the exact browser command on existing Linux that permits ordinary
Chromium sandbox and sockets. PASS is emitted only after all assertions complete.

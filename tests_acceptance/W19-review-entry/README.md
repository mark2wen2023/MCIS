# W19 applied-query browser acceptance
Product base: 80d558101f9fa9fec628dd518e40fbec5faf165c.
Extends the existing bf243672cea8ffb39de0682e5095a1ca4559781d test directory.
No product source changes. Existing entry.tsx fixture is reused byte-for-byte.
pins.json now includes SearchReason and the exact updated KnowledgePage (12 source files).

Run with existing dependencies on an approved Linux browser host:
node tests_acceptance/W19-review-entry/run.cjs --web-deps /existing/web/node_modules --chromium /usr/bin/chromium
Optional --playwright /existing/node_modules/playwright.
Build only (does not launch a browser):
node tests_acceptance/W19-review-entry/run.cjs --web-deps /existing/web/node_modules --check-build

Original keyboard open/no-source-request/version reload assertions remain.
Review details are now selected by their summary rather than "first details", because
the actual product has a separate search-reason disclosure before the source disclosure.

New browser assertions:
1. Submit existing synthetic text “原因未核”; retain returned applied explanation.
2. Edit the input to “告警” without submitting: explanation and request count unchanged.
3. Submit explicitly and hold the Candidate response: loading has no old result card/reason.
4. While loading, switch existing status control to Published (search submit is disabled).
   Fulfill current synthetic response, then deliver the older Candidate response.
5. Confirm older JSON was actually parsed, allow React continuation, and assert current card
   plus explanation remain byte-identical. No new write/foreign request permitted.

Explicit test boundary: a test-only fetch wrapper removes AbortSignal ONLY for the intercepted
same-origin knowledge/cards GET. Response bytes still come through the intercepted HTTP route.
This deliberately models abort-insensitive delayed transport to exercise product cancelled guard;
it is not ordinary browser cancellation, real server ordering, permissions or authentication.
The wrapper logs completed JSON parse so a cancelled/never-delivered request cannot count as PASS.
No production fetch/API code is modified. No source site or actual backend contacted.
Fixed v1/v2 texts and existing sample Content only; Published is test transport status, not a save.

Actual Linux results this turn: node --check exit 0; --check-build exit 0, 12 pins verified.
Browser NOT RUN, per instruction not to repeat known socket/Chromium blockage.
All interaction/late-response assertions remain pending coordinator verification.
chromiumSandbox:true remains mandatory; no --no-sandbox, services, installation or CI.

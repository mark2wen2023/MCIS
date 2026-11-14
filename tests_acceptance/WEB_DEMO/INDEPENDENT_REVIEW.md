# Independent web-demo boundary review

Scope: isolated fictional loopback demonstration only. Product code was read, not changed by reviewer. This is not production authentication, a general bearer proxy, a persistent case workstation, or browser acceptance.

## Review verdict
No blocking issue found within the narrow fixed-fixture boundary. Server accepts only fixed choice values, creates no durable browser identity, and calls the existing temporary run_demo flow. Internal trial account credentials never enter browser responses. Legacy routes and default apps are not mounted or changed. CLI binds a retained IPv4 loopback socket at a random port and disables proxy-header interpretation. Origin, Host, independent nonce, strict request shape, body budget, lifetime and execution limits are checked.

Cancellation retains the task and its single execution slot; lifecycle shutdown waits for it. Generic server errors do not expose internal exception details. Static rendering uses textContent, CSP, no-store, no CORS/cookies/storage credentials.

## Verification
- Independent ASGI suite: 18 passed, zero skipped. Covers repeated/security headers, duplicate keys, invalid body values, oversized and malformed input, request cancellation, concurrent admission denial, shutdown draining, expiry recheck after body, disconnect before dispatch, sanitized errors and response headers.
- Combined primary + independent web tests: 31 passed, zero skipped, with actual W2 core wrapper enabled.
- Actual HTTP: in one tool process, started CLI subprocess, read served HTML using urllib, extracted demo-only CSRF nonce, POSTed both fixed sources. Actual result delta=5, temporaryDataCleaned=true, productionLogin=false. Terminated subprocess afterwards. This confirms local TCP HTTP behavior for that process environment, not GUI/browser accessibility or operating-system-wide network isolation.
- Parent reported CUA browser ERR_CONNECTION_REFUSED. No browser-through-UI pass is claimed.

## Remaining limits
- No production account login, real case upload, intranet data, or durable result history.
- Same-machine privileged processes are not isolated by a CSRF nonce; scope is deliberately synthetic.
- Cleanup verified for normal completion and controlled request cancellation/draining, not power loss or forced kill.
- Browser click/render/end-to-end acceptance remains unverified.

## Independent frontend follow-up
Reviewed updated demo.js: pagehide and selection change clear visible prior output and invalidate request epoch; all choice controls and run button are disabled while a current request is active. Old completion/finally paths cannot paint or unlock a newer request. Fixed summary validation checks synthetic case/source selection, completed temporary save/read/cleanup, unreviewed and non-production markers, source/version limitations, bounded finite degree deltas and constrained run identifier. Output is assigned through textContent, not HTML.

Ran primary `node web/tests/web-demo-dom.mjs` successfully. Added and ran `node web/tests/web-demo-dom-independent.mjs`: 17 malformed/mismatched summary variants rejected; overlapping old/new request preserves newer lock and hides stale result; changing choice removes previous result and rejects source-mismatched response; valid single-source no-conflict result displays with caution; no injected markup or local/session storage. No product changes made by independent reviewer.

These are happy-dom simulated DOM checks, not a browser-engine render, click, CSP enforcement, or network end-to-end acceptance. Actual CUA browser remains unverified/refused as separately documented.

## Opt-in Chromium harness review
Read `web/tests/web-demo-browser.mjs` independently. No blocking issue found within the trusted-local-executable test harness boundary. Chromium sandbox remains enabled; browser is launched before the Python service so unavailable Chromium cannot start the demo listener. Origin comes only from the harness child and is validated as numeric IPv4 loopback port. Fresh browser context blocks service workers; route allowlist rejects external/legacy requests. Three genuine click paths require precise W2 display and source-count expectations. Inline CSP probe injects a DOM script rather than treating evaluate as CSP-controlled. Cookies and web storage are asserted empty. Screenshots use a unique mkdtemp directory, avoiding pre-existing file replacement.

Independent controlled-stub failure checks (`python tests_acceptance/WEB_DEMO/check_browser_harness_failures.py`) passed three cases:
1. launch rejection => BLOCKED exit 1, no service spawn;
2. context rejection => FAIL exit 1, browser close invoked, no service spawn;
3. child emits non-loopback origin => FAIL exit 1, browser close and child SIGTERM cleanup observed.

These controlled stubs exercise failure reporting and ownership/cleanup only. They are not a Chromium run, CSP enforcement test, screenshot acceptance, or actual browser-to-W2 result. Real sandboxed Chromium remains blocked as recorded by the primary worker. No product security defaults were changed. No merge/deployment performed.

# Isolated web demo DOM acceptance

Requires Node plus HappyDOM test dependency (also used by existing frontend acceptance
scripts); run `node web/tests/web-demo-dom.mjs` from repository root. Product has no
new frontend framework/runtime dependency. This script loads the actual demo assets
and uses controlled fetch responses. Checks successful5deg display, repeated click,
disabled controls, selection invalidation, pagehide/late response,429, rejected shape,
and no local/session storage. Not actual browser, network, W2 or CSP enforcement.

Actual Python ASGI/W2 and subprocess loopback tests are separately documented in
service/tests/test_web_demo*.py and tests_acceptance/WEB_DEMO/INDEPENDENT_REVIEW.md.

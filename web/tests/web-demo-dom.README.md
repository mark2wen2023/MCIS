# Isolated web demo DOM acceptance

Requires Node plus HappyDOM test dependency (also used by existing frontend acceptance
scripts); run `node web/tests/web-demo-dom.mjs` from repository root. Product has no
new frontend framework/runtime dependency. This script loads the actual demo assets
and uses controlled fetch responses. Checks successful5deg display, repeated click,
disabled controls, selection invalidation, pagehide/late response,429, rejected shape,
and no local/session storage. Not actual browser, network, W2 or CSP enforcement.

Actual Python ASGI/W2 and subprocess loopback tests are separately documented in
service/tests/test_web_demo*.py and tests_acceptance/WEB_DEMO/INDEPENDENT_REVIEW.md.

## Optional real Chromium acceptance (trusted same machine)

`web/tests/web-demo-browser.mjs` is a separate opt-in acceptance entry point, not a
production workbench or a substitute for browser verification. Requires an installed
Playwright package, a sandbox-capable Chromium, service dependencies and the actual
W2 executable. It starts its own five-minute loopback-only demo; an external target
URL and existing browser profiles are not accepted. No real credentials/data.

```
MCIS_DEMO_PYTHON=/absolute/path/to/venv/bin/python \
MCIS_PREFLIGHT_REAL_CORE=/absolute/path/to/trusted-w2-command \
node web/tests/web-demo-browser.mjs
```

Optional `MCIS_CHROMIUM_EXECUTABLE` selects an installed trusted Chromium binary;
`MCIS_PLAYWRIGHT_MODULE` selects an installed trusted Playwright package, not an
untrusted download. `MCIS_BROWSER_ARTIFACTS` selects a local output parent; each run
creates a unique directory, so existing screenshots are not overwritten.
The browser sandbox stays enabled. The runner closes browser/server on completion.

Checks real clicks for both/first/second fictional sources, 5-degree comparison,
source counts, unreviewed/cleanup notices, empty cookies/storage, same-origin
allowlisted requests, and blocked inline-script execution under CSP. Uses actual
core; no HTTP/result stubbing or mock fallback. Startup or assertions failing exits
nonzero. A successful run only verifies this isolated fictional demo, never
production identity, real investigation data, LLM, or the existing workbench.

Current cloud execution: **BLOCKED**, not passed. Installed Chromium fails to create
its process-singleton socket (`Operation not permitted`) with normal sandbox and
with authorized execution. The runner reports `BLOCKED` and exits 1 before starting
the demo. The earlier CUA browser returned `net::ERR_CONNECTION_REFUSED`; these are
two observed failures, not a proven common root cause. No `--no-sandbox`, public
listener or tunneling was used. Previous HappyDOM and ASGI/HTTP results remain
separate from true browser rendering and interaction acceptance.

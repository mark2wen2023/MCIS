# Same-machine browser acceptance follow-up

## Actual findings

- Available environment inventory: one connected cloud computer; no separately
  connected user computer was selected or required.
- Installed `/usr/bin/chromium` was tested with its normal sandbox. Both normal
  execution and authorized execution failed at the process-singleton socket:
  `socket() failed: Operation not permitted` (with a secondary ptrace denial).
- Earlier CUA navigation returned `net::ERR_CONNECTION_REFUSED`. These observations
  do not establish that the two failures share one root cause.
- No sandbox-disabling arguments, proxy exposing loopback, public tunnel, port
  forwarding or production service deployment was used.

## Added acceptance entry point

`web/tests/web-demo-browser.mjs` is opt-in and uses Playwright with
`chromiumSandbox: true`. Browser startup happens before the temporary demo server,
so the tested failure left no server running. On a trusted same-machine host it
will launch its own fixed loopback demo, click the three fictional choices using
actual W2, verify displayed values/counts/warnings, CSP inline-script blocking,
empty storage and bounded requests, then close browser and server. Screenshot
outputs use a fresh unique directory. No external target, credentials, existing
profile or real-case uploads are accepted.

## Validation and honest scope

- Node syntax check passed.
- Actual runner invocation: `BLOCKED: sandboxed Chromium unavailable; no browser
  acceptance claimed.` Exit 1. No screenshots or browser pass were obtained.
- Existing primary and independent HappyDOM suites rerun and passed. They remain
  controlled DOM tests, not browser layout/CSP/network acceptance.
- Existing web service primary+independent regression rerun: 31 passed, zero skips,
  including actual W2. One existing Starlette/httpx deprecation warning.
- The earlier full 448-test pass is historical, not rerun for this test/doc-only
  change. No product or auth defaults changed; CI is separate from these local runs.

## Still not delivered

Production login, real-case browser authorization/session transport, migration of
legacy unprotected routes and actual workbench integration are not implemented by
this runner. The fictional demo is not the MCIS product deliverable. A host capable
of creating the browser's required sockets while preserving its sandbox is needed
to execute the real-browser acceptance before marking it passed.

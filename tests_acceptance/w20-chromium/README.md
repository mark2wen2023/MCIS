# W20 current-source human acknowledgment: Chrome candidate

Test tooling only against fixed MCIS `e15f98267936bb2ba26a1a8c845df7410db8c8d1`.
No product source, contracts, API action, or permission changes. This test wrapper
serves the exact product web bundle and unmodified FastAPI using a temporary
SQLite database, a controlled synthetic model fixture (no inference), and only
an ephemeral 127.0.0.1 listener. Existing role header setup is for the synthetic
fixture, not authentication/cutover. The runner uses exact Git blob pins for 156
web sources, 146 service sources, 73 contract files and one fixed synthetic
fixture. Checked files are copied to an ephemeral source root; no changes to
the supplied checkout. No installs, downloads, credentials, real data, CI,
or production. Use Python 3.12 with existing Playwright (must offer
`BrowserContext.route_web_socket`), existing `esbuild`/web dependencies and
separate existing Python service environment.

From the repository root at the exact product + these test files:

```sh
runner=tests_acceptance/w20-chromium/run.py
# Build and pins; no server or browser:
python3 "$runner" --source "$PWD" --node-modules /existing/web/node_modules --build-only
# Explicit HTTP-only fallback, not a real browser receipt:
python3 "$runner" --source "$PWD" --node-modules /existing/web/node_modules \
  --host-python /existing/service/venv/bin/python --http-only --evidence /work/w20-http-new
# Actual sandboxed Chrome:
python3 "$runner" --source "$PWD" --node-modules /existing/web/node_modules \
  --host-python /existing/service/venv/bin/python \
  --browser /existing/path/google-chrome --evidence /work/w20-browser-new
```

Evidence directory must not exist. Runtime subprocesses and temporary DB / source
are cleaned. Browser and fixture statuses are intentionally separate:

- Desktop browser component fixture mounts the exact product `DraftReview`.
  Local synthetic props exercise identical, changed, missing, ambiguous quote,
  ambiguous round and restored context. Invalid states cannot confirm.
  Restoration requires a fresh checkbox before one local callback. This fixture
  makes no service writes, and passing here does not imply those props can be
  produced by the application's current protected interview API.
- The actual W5 InterviewPage uses existing current-case reads, extraction and
  review; select the record in the normal product deep link. Desktop browser
  clicks extraction and checks the source. The runner then appends one new
  synthetic turn using the existing service; the stale browser review returns
  exactly 409 `SOURCE_CHANGED` with no committed statement. One review write
  attempt only. Stop/restart the actual service on the same SQLite; in a fresh
  browser context at 390×844 the same draft must remain pending and unchecked,
  zero statements and no review POST. 390 is readback, not UI responsiveness
  sign-off. Real report extraction / model quality / other LLM roles are not
  tested.
- Browser disables service workers, blocks WebSockets and non-origin page
  requests, and fails on either or a page exception. Chrome headless is run
  with `chromium_sandbox=True`, never `--no-sandbox`. Do not substitute mocks
  or alter assertions in response to environment errors. Report exact SHA,
  normal sandbox Chrome version, command/exit, receipt/logs and three synthetic
  screenshots when the actual browser path succeeds. No failure data is
  considered an acceptance receipt.

Local preflight: pin/build succeeded; HTTP-only actual service returned
`SOURCE_CHANGED` and SQLite restart kept one pending draft, zero statements.
True-browser command attempted: Chromium wrapper exited 127 because
`/usr/lib/chromium/chromium` did not exist; runner exited 1 before browser or
server startup. No real browser validation or screenshots in this workspace.

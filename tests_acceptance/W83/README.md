# W8.3 independent acceptance

No implementation code is changed by these tests.

## Run

From repository root, with dependencies already installed:

```sh
node tests_acceptance/W83/build-lifecycle.mjs
node tests_acceptance/W83/.tmp-lifecycle.cjs
MCIS_BROWSER_BIN=/absolute/path/to/chromium python tests_acceptance/W83/browser_test.py
```

`python` must have the existing Playwright package available. `service/.venv/bin/python` must contain service dependencies. Set `MCIS_W83_PYTHON` to override the service interpreter, `MCIS_W83_SERVICE_ROOT` to override the service source, and `MCIS_W83_ARTIFACT_DIR` for outputs (default new temporary directory). No browser or package is installed by the runner. Browser, Vite and uvicorn are launched in the same process tree so sandbox loopback namespaces do not break access. Ports: **127.0.0.1:18883** service, **127.0.0.1:15883** UI; ensure free before running. The runner terminates its own server groups in finally.

The small qa_app uses the actual repository create_app with production seeding disabled, then seeds only the fictional Lily/Mary fixture into a newly created temporary SQLite/blob directory. It does not read/modify user service/data, production data or public-report fixtures. No import endpoint is called.

## Coverage classification

- `http_test.py`: actual loopback HTTP export→ZIP→manifest verification, hash tampering/missing/extra, format errors, role restrictions, case-list unchanged. Must be run with the test service available (browser runner does this).
- `browser_test.py`: real Chromium actions/download and real service for happy path and package integrity. Explicit route mocks only for server failures, malformed responses and delayed/race responses. Does not claim mocked failures are real-server behavior.
- `lifecycle.tsx`: independent component/async logic harness using deterministic mock React hooks, fetch and DOM download target. Not a real React renderer or browser; supplements, never replaces, browser evidence.
- Outputs include screenshots, fixture archives, logs, JSON results. Only source scripts, text/JSON result evidence and review documents belong in commits; no runtime service copy, generated CJS, archives, SQLite or browser binaries.

## Browser tooling

CUA browser was attempted first but could not reach the exec-local servers (`ERR_CONNECTION_REFUSED`). Engineering-test authorization permitted the existing local Playwright fallback; no new software installed. Final service runtime was checked against integrated main e8db196: all 78 Python files match exactly; final runs record overrides or use the full main checkout. This is a W8 package/UI slice, not a full-service baseline or deployed acceptance.

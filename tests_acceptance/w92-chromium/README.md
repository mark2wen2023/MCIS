# W9.2 environment save recovery: exact-source genuine Chromium gate

Test-only harness for product `26dd466fcbdeb8422fcb54a5985d93df2103f4cc`, synthetic input only. It bundles the exact React environment page into a test shell and runs original FastAPI on a loopback host with a fresh SQLite file. It is not the full product shell or production sign-off. Use existing Python/Playwright supporting `BrowserContext.route_web_socket` and `Route.fetch(max_retries=...)`, Chromium executable, frontend dependencies and service Python requirements. Do not install or disable sandboxing.

From the pinned checkout root:

```sh
runner=tests_acceptance/w92-chromium/run.py
python3 "$runner" --source "$PWD" --node-modules /existing/web/node_modules --build-only
python3 "$runner" --source "$PWD" --node-modules /existing/web/node_modules \
  --host-python /existing/service/venv/bin/python --http-only --evidence /new/w92-http
python3 "$runner" --source "$PWD" --node-modules /existing/web/node_modules \
  --host-python /existing/service/venv/bin/python --browser /existing/google-chrome \
  --evidence /new/w92-browser
```

Use a new absolute evidence directory per run. In actual Chrome on desktop, the local test harness forwards the fixture POST once to the real service, waits for 201, then drops only delivery of the successful response. The page must show an uncertain result until explicit read-only recovery, find the already registered row, and not issue a second POST. After service restart on the same SQLite, a new 390x844 browser context reads the same case and separately checks the other synthetic case is empty. Existing stored content, the synthetic source, zero value and unknown time semantics must be preserved. Assert one stored row and one audit. Successful genuine-browser mode emits four synthetic screenshots and a receipt.

The HTTP-only command verifies real single registration/audit, restart, exact readback and synthetic case separation, not UI recovery. It passed locally. The local Chromium command exited 127 before page execution because its binary was missing; a true-browser pass is still pending. No dynamics, full app shell, live data, external traffic, model, real identity, or production.

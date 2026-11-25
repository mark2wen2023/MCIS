# W7 browser acceptance: deadline provenance after reopening

Candidate: MCIS `b2ecb50b32b721c9f171b74ecd576691c0048b94`. Use its exact complete
web/service exports and already installed dependencies. The runner checks all
three relevant product blob IDs before launching. Node Playwright 1.48+ or
compatible existing playwright-core is required for the browser path; no
installation or download is performed.

```sh
python3 -B tests_acceptance/w7-deadline-chromium/run.py \
  --web /exact/b2ecb50/web --service /exact/b2ecb50/service \
  --service-python /existing/service/.venv/bin/python \
  --browser /existing/chromium --playwright /existing/playwright/index.mjs
```

The driver requires a normal sandbox and never disables it. Vite is staged
into a temporary app copy with its cache/config runner in temporary storage.
Both processes listen only on loopback; browser page HTTP/WS routes refuse any
other origin before first navigation. This is not a machine-wide packet capture.
No real case, real identity, sends, recommendation creation, W7.5, evidence
source binding, production authentication, remote tests or deployments.

The actual Recommendations page must verify:
- Default 30 days vs explicitly marked 45 days, distinct confirmation text,
  no write before confirming, and no days field on the default wire payload.
- Both synthetic rounds get a locally recorded reply and explicit closure;
  UI text does not imply the system sent anything or independently verified
  agreement.
- Restart FastAPI over the same SQLite; the browser reopens both closed rounds
  with original version and stored 30/45-day UTC intervals. Audit has exactly
  two open / two reply / two close actions with distinct default/declared
  provenance and valid hash chain. Reopening adds no writes.

Run the same command with `--http-only` in place of the last two options for a
distinct loopback readiness/lifecycle check without Playwright or Chromium.
This local HTTP-only check passed twice, verifying Vite proxy, actual API and
SQLite process reopen (six audit events). Node browser file syntax checked,
but the real Chromium path is **blocked here**: the system launcher exists
and its payload `/usr/lib/chromium/chromium` does not. That result is not a
browser pass; an already working sandboxed Chrome executor is required.

The official runner stages Vite into a temporary web copy. The pinned product
imports `contracts/schemas/report.schema.json` from outside `web/`; the harness
therefore also places a read-only symlink to that existing product `contracts/`
directory beside the staged copy (product files are not modified). Optional
`--out /path` writes official flow screenshots from the same sandboxed browser
run. `--http-only` remains a distinct preflight and is not a browser pass.
 After the required FastAPI/SQLite restart, the driver reloads the already-open Recommendations page so the panel does not stay on a hung pre-restart fetch (same-hash goto is not a reload).
 The staged Vite proxy disables HTTP keep-alive so FastAPI restart on the same loopback port does not leave the proxy holding a dead backend socket.
 After reload, the driver does not re-select LeadInvestigator when that role is already active, because a same-role identity event cancels the in-flight consultation load without remounting the panel.

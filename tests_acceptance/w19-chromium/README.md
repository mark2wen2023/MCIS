# W19 real sandboxed Chromium acceptance

Candidate: MCIS `b3b8ae36e7eaeac759eecb7f136ca46e77dc6571`. Use its exact
web and service trees and pre-existing dependencies. This script validates the
two released UI file blobs. No versioned files are changed; Vite may maintain its local cache. It must not be
run against real case data, user accounts, external services or a browser without a
working OS sandbox.

```sh
/absolute/existing/python-with-playwright tests_acceptance/w19-chromium/check.py \
  --web /absolute/fixed/web --service /absolute/fixed/service \
  --service-python /absolute/existing/service/.venv/bin/python \
  --browser /absolute/existing/chromium \
  --out /absolute/screenshot-dir
```
`--out` is optional and writes full-page PNGs of the real Knowledge flow.
The create-form fields are filled through `details.w19-create label` text,
not `get_by_label(..., exact=True)`, because after “填入合成示例” Playwright
includes the textarea value in the accessible name of `<label>标题<textarea>`.
The selector and review/restart/withdraw control flow originate from the known browser harness at MCIS `9d7d84326d050f004b633fd80f27a38297d7b135`. This is tests-only.


Playwright must already support BrowserContext.route_web_socket (1.48+). No
dependency install and no fallback to --no-sandbox; absence or failure is not a
pass. The option --http-only uses no browser/Playwright to verify both actual
loopback listeners, Vite's proxy to FastAPI, temporary SQLite, two genuine no-write template responses, review and restart,
and public denial. It prints a distinct result. The real browser uses the actual
Knowledge page and demo role selector, not a replacement UI or mocked network
response. It restricts browser page traffic to the loopback Vite origin, blocks
service workers, and asserts zero attempted off-origin traffic. This is not a
machine-wide network capture or a production login/authorization test.

Required acceptance: true Chromium launch with sandbox. Apply one genuine
offline template preview, edit the source, show stale warning while preserving
the old candidate body, and reject both UI and submit-handler saving. Restore
the old source text and verify saving remains blocked. Before recovery no
card POST, no record and no audit. Apply a fresh preview for the revised
source, then exactly one deliberate synthetic create
as internal lead; exact-ID readback read-only while Candidate; Public list and
direct API deny; audit-bound explicit three-checkbox publication from the real
form; process restart on same SQLite; unchanged digest, source and review note
on real by-ID reopen; explicit withdrawal from separate list controls, reopened
internal view Withdrawn and Public list/detail deny; 3 writes in audit, verified
chain, no external requests. Server/browser state cleaned afterward.

Observed locally: --http-only PASS with actual loopback Vite and FastAPI, native
SQLite restart; sandboxed Chromium path BLOCKED (wrapper exists, browser payload
missing under /usr/lib/chromium). Browser path and DOM selectors are not claimed
executed; independent bash/python runner validation is separate.

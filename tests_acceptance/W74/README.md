# W7.4 independent acceptance

All data are synthetic; no model, real reports, external sending or deployment.

## Evidence types
- `browser_interruptions.py` mounts the **unchanged actual reader component** in a temporary Vite test document. Playwright supplies synthetic API responses/delays. This tests UI state isolation, not backend authorization: keyboard open; independent audit403; clear-on-refresh; close/reopen; recommendation/case prop changes; hash navigation; operator identity changes; late body/audit response discard; malformed whole batch; empty fields; mobile; Public no reader requests; GET-only. The temporary document is removed after execution.
- `projection_acceptance.ts` tests the actual pure content/history projection using synthetic values, including invalid reply beyond the first displayed page and omitted raw fields.
- Re-executed `web/tests/recommendation-review-w74-real-browser.py` uses **actual loopback FastAPI and Vite**, a temporary SQLite database seeded only with fictional Lily/Mary and sentinels. It verifies page embedding, 12-response pagination, literal HTML text, separately authorized audit, close/refresh reset, actual server denials and unchanged audit count. This is not a response double.
- `service/tests/test_recommendation_review_w74.py`: 6 real route tests through TestClient and temporary synthetic SQLite.

Commands (from repository root):
```
MCIS_BROWSER_BIN=/path/to/authorized/chrome-headless-shell python tests_acceptance/W74/browser_interruptions.py
web/node_modules/.bin/esbuild tests_acceptance/W74/projection_acceptance.ts --bundle --platform=node --format=cjs --outfile=/tmp/w74-projection-acceptance.cjs
node /tmp/w74-projection-acceptance.cjs
MCIS_BROWSER_BIN=/path/to/authorized/chrome-headless-shell python web/tests/recommendation-review-w74-real-browser.py
```
Use the installed, authorized browser executable appropriate to the environment; the placeholder above must be configured for the local environment.

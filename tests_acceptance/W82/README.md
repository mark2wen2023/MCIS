# W8.2 independent acceptance

- `service/.venv/bin/pytest -q tests_acceptance/W82/test_http.py -p no:cacheprovider`: real TCP HTTP against a subprocess service, no TestClient. Temporary SQLite, no seed, dynamically selected localhost port.
- `python tests_acceptance/W82/browser.py`: system Python Playwright drives actual official Chrome headless shell at `/tmp/w8-headless/chrome-headless-shell-linux64/chrome-headless-shell`, Vite and the same isolated service. America/Los_Angeles browser zone demonstrates explicit UTC behavior. All services bind only 127.0.0.1 and are stopped afterward.
- Browser scenarios explicitly distinguish real HTTP from route-injected response faults. `route.fetch()` forwards POST to real backend before discarding or delaying its response; resulting audit records are checked via separate real HTTP reads. 403/422/500/malformed-success/mismatching-GET are synthetic response tests, not evidence of server behavior.
- `/usr/bin/chromium` cannot start here because Unix-domain sockets are restricted; both original startup attempts are retained in logs. No system security setting was changed.
- Output: `artifacts/results.json` and layout screenshots; summary in `logs/w8.2-independent-review.md`.
- Existing service date-time schema enforcement gap is a strict xfail, not a W8.2 fix. No implementation or old test files modified by acceptance.

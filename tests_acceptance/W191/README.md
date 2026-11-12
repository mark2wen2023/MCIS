# W19.1 independent acceptance

Run from repository root:

```sh
service/.venv/bin/pytest -q -p no:cacheprovider tests_acceptance/W191/test_http.py
```

Tests start real Uvicorn TCP servers on ephemeral `127.0.0.1` ports, use `httpx` with environment proxies disabled, and clean up their servers. SQLite and all fixtures live in pytest temporary directories; no real reports or private case materials are loaded. A local-socket-capable execution environment is required. The selected service virtual environment supplies pytest, httpx, uvicorn and SQLAlchemy.

Coverage: all six existing roles; Case/Challenge/Method lifecycle and full detail; unpublished/withdrawn isolation; public responses omit reviewer/author/reason/approvals; literal `%`, `_`, backslash, HTML, Unicode case-fold and emoji searches; exact tags; pagination and bounds; approval type strictness; invalid Unicode/control/oversized input; explicit public-source permission; eight concurrent reviews; independent hash recomputation; append-only triggers; creation and withdrawal rollback when an audit INSERT is rejected by a temporary test-only database trigger.

The role headers are declarations in a local demonstration, not production authentication. Source links are synthetic example URLs and are not visited or represented as licensed real evidence. No model, training, deployment, upload, or automatic case import is exercised.

Browser acceptance (dependencies supplied by environment):

```sh
W191_PLAYWRIGHT=/path/to/playwright/module \
W191_CHROMIUM=/path/to/chromium \
bash tests_acceptance/W191/browser-run.sh
```

The runner starts/stops service and Vite in one session. B01–B08 includes real committed requests with delayed/lost responses, identity/navigation invalidation, known write failure persistence, explicit unknown-result reconciliation, double-click protection, HTML escaping and 390px keyboard layout. Network-fault injection is engineering Playwright fallback, not a production-device qualification.

v1 results remain in `logs/w19-independent-browser.log`; v2 retest results are in `logs/w19-independent-v2-*`. B07 and B08 assertions were not changed between red and green runs.

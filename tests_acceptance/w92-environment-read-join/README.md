# W9.2 synthetic environment read integration

Use this offline check with the fixed MCIS checkout
`a928e5e4db6d0bd669a41b80a8f5d39a707cab98`. It complements the earlier
`tests_acceptance/W92/` suites by verifying this commit's explicit separation
between an environment observation and an approved replay input.

```sh
node tests_acceptance/w92-environment-read-join/run.cjs \
  --source /path/to/fixed/MCIS \
  --python /path/to/service/.venv/bin/python \
  --web-modules /path/to/web/node_modules \
  --happy-dom-entry /path/to/happy-dom/lib/index.js
```

Use an existing service interpreter with its FastAPI, SQLAlchemy, httpx and
schema dependencies and existing web modules (React, React DOM, router and
esbuild). There is no dependency install, listening socket or browser launch.
The runner stages 73 files only after each matches its pinned Git blob hash.
Missing or mismatched bytes fail before either fixture or frontend runs. Bundles,
database and synthetic files live only in a temporary directory and are cleaned
up; no response bodies or private paths are recorded in the repository.

The fixture uses the case and environment routers, temporary SQLite and the
existing role/access policy. It creates one wholly invented case and two
environment observations using the actual API. A Public read goes through the
real role checks. Then a fixture-only policy update denies Public environment
access (the case metadata still reads); a different nonexistent case returns
404. The actual EnvironmentPage receives the unmodified ASGI response bytes
after SHA-256 verification via local child-process IPC.

The 21 assertions cover the two distinct location cards, zero versus unknown
current, no tide-to-current inference or dynamics wording, clearing on denial
or missing case, and no write form or replay fetch. The six actual statuses are
200/200, 200/403 and 404/404 (case metadata / environment observations); error
responses do not expose observation descriptions. No raw response payloads
are emitted; the stdout summary shows only synthetic paths and
statuses, along with SHA-256 values.

This verifies React in Happy DOM, not a real browser, production identity,
a structured spatial/time applicability boundary, navigation replay, dynamics,
or full application acceptance. Location descriptions are text labels only.

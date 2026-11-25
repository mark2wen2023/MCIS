# W9.2 create, reconcile, and reopen

Product bytes pinned to MCIS `aca3e1e120b955ef25baefc58ef57f83758651d8`.
The 73 Git blobs are identical to the product source covered by the existing
read-only join at `a928e5e4db6d0bd669a41b80a8f5d39a707cab98`. This complements
that test; no product files are changed.

```sh
node tests_acceptance/w92-environment-create-reopen/run.cjs \
  --source /path/to/fixed/MCIS \
  --python /path/to/existing/service/.venv/bin/python \
  --web-modules /path/to/existing/web/node_modules \
  --happy-dom-entry /path/to/existing/happy-dom/lib/index.js
```

Uses already-installed React, React DOM, router, esbuild, Happy DOM, FastAPI,
SQLAlchemy, httpx, and schema dependencies. The runner stages only pinned bytes.
The two actual product routers run through in-process ASGI TestClient with an
isolated on-disk SQLite database; the actual EnvironmentPage and form use
React/Happy DOM. GET/POST calls are bridged only by local child-process IPC.
Product responses are checked against their SHA-256 before use.

The actual form submits one invented record. One actual API request commits the
record and responds 201; the harness deliberately loses that response before
it reaches React. The form shows uncertainty, does not optimistically display
a card, and its read-only check confirms the saved record without retrying the
POST. Then the database engine is disposed and a new Database connects to the
same on-disk file. A fresh Public view reads the same bytes and displays the
record's source and location verbatim, an observed numeric zero, and no
invented UTC for an unknown time. Switching to another fictional case does not
show the record.

Database checks require one stored observation, one observation-write audit row
with the recorded actor/action/entity, and a verified audit chain, including
after reopening and refusing conflicting-ID (409), Public-write (403), and
wrong-case (422) attempts. Rejected operations do not overwrite the original
or add a duplicate audit row. No product replay request or environment
dynamics is invoked. Temporary staged bytes, bundle and DB are removed.

This is not a true browser test, production authorization, or integration with
the replay engine. The identity is a local demo role, and the environment record
is explicitly not an approved replay input.

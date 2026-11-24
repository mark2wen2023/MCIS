# W19 published-card withdrawal and read lifecycle

Fixed source: MCIS `7ba7970ba4f77ebce11463d663e0f02a6c3f7928`. Both tools independently verify the exact Git blobs of their input code before running. They use already-installed packages, no downloads, GitHub actions, database seeds, real cases, external account or model.

Install nothing as part of this smoke test. From a checkout that contains the pinned product sources and these tools:

    /path/to/existing/venv/bin/python -I -B tests_acceptance/W19-read-lifecycle/api_check.py
    MCIS_HAPPY_DOM_PATH=/path/to/existing/node_modules/happy-dom/lib/index.js \
      node tests_acceptance/W19-read-lifecycle/run-portable.cjs

The Python script accepts `--checkout /path/to/pinned/checkout`. The Node script accepts an optional pinned source checkout path as its first argument; set `MCIS_NODE_MODULES` to the existing React/esbuild node_modules if it is not in that checkout's web/node_modules. The Node bundle is generated outside the checkout and deleted even on failure. A pin mismatch, failed assertion or timeout exits nonzero.

## What ran

- Actual unmodified Knowledge router, request context and SQLAlchemy with FastAPI TestClient and isolated temporary on-disk SQLite: 49 assertions. A synthetic investigator creates a candidate and the lead explicitly approves publication then withdraws it. Four external demo roles can query Published and receive redacted details, then see empty results/404 after withdrawal and SQLite reopen. Rejected writes, audit/chain checks, internal history and absence of archive import all verified. Demo role headers are not production authentication.
- The existing actual KnowledgePage and KnowledgeCard React test is reused unchanged. Thirty-five assertions through HappyDOM simulate controlled GET responses: stale disclosure/source do not survive reread, withdrawal, permission/error, context change, or late unmount response. This is not an actual browser. Transport is intentionally separate from the real API; these are not a joined end-to-end run.

The existing backend unit tests cover lifecycle/roles, and the existing React runner covers component behavior. The added tool verifies the withdraw/reread behavior across SQLite reconnect and makes the already committed React check reproducible without generating files inside a checkout.

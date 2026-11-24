# W17 synthetic evidence selection and registration receipt

Run against the fixed MCIS checkout at `29cbfe255967fc6814abafd919ed9a7485ef8710`.
Use the MCIS service interpreter with its existing dependencies and the installed
web dependencies (React, React DOM, React Router, esbuild). Supply the entry point
of an existing Happy DOM installation. This test does not download dependencies,
start an HTTP listener, call remote services or launch a browser.

```sh
node tests_acceptance/w17-evidence-selection-receipt/run.cjs \
  --source /path/to/fixed/MCIS \
  --python /path/to/service/.venv/bin/python \
  --web-modules /path/to/web/node_modules \
  --happy-dom-entry /path/to/happy-dom/lib/index.js
```

The runner checks 100 Git blob hashes before execution and stages only those
bytes; missing or mismatched input fails before running either suite. No
generated outputs, bundles, fixture databases or response bodies are published.
Temporary bundles and synthetic SQLite/file storage are cleaned by the runner
and the fixture hosts. Run the command to get fresh summaries; it exits
nonzero on failure.

- **Selection (20 assertions):** actual evidence list and custody endpoints
  with temporary SQLite and demo roles; two fictional cases deliberately reuse
  one evidence ID. Explicit row selection controls the custody read. Switching
  cases clears old selection, and late responses do not repopulate it. Public
  denial does not return the selected evidence. Selection only exercises
  synthetic metadata seeded for this independent control.
- **Registration receipt (30 assertions):** the actual preview and commit
  endpoints register independently invented file bytes in two fictional cases.
  Receipt metadata only appears after the explicit read action. The read must
  match the registered case, evidence ID, digest and source bytes; a stale
  case response, wrong case/digest/evidence and revoked role do not expose it.
  The database ends with only two registration custody records and two audit
  events, with no extra access records. Neither test downloads source bytes.

Each browser-side check runs the actual EvidencePage and API helpers in Happy
DOM, using the source HTTP response bytes from FastAPI TestClient via local
child-process IPC. This is not Chromium, a deployed backend, real
authentication, a real original-file preview or the archive acceptance path.
Auxiliary UI routes intentionally return ASGI 404. Demo role headers do not
prove production authorization. The receipt is registration metadata, not
evidence authentication, a review-run binding or proof of original-file access.

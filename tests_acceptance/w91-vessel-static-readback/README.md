# W9.1 static parameters and source read-back

Product bytes pinned to fixed MCIS `26dd466fcbdeb8422fcb54a5985d93df2103f4cc`.
This complements existing W91 storage and browser checks with the current
`ShipsPage` + `Dimensions` display reading from the actual persisted API
record. No product file is changed.

```sh
node tests_acceptance/w91-vessel-static-readback/run.cjs \
  --source /path/to/fixed/MCIS \
  --python /path/to/existing/service/.venv/bin/python \
  --web-modules /path/to/existing/web/node_modules \
  --happy-dom-entry /path/to/existing/happy-dom/lib/index.js
```

68 source Git blobs must match before running. React/Happy DOM executes the
actual `/ships?case=...` entry, passing local IPC HTTP calls to real FastAPI
TestClient against a temporary on-disk SQLite database. Its response hashes
are checked before delivering raw response bytes to the product API client.
No dependencies are installed, no browser/socket/network opens, and temporary
staging and the DB are cleaned up.

The real form rejects an invalid zero beam locally, then stores one synthetic
vessel. A direct declared plan length is labeled not independently verified;
a zero estimated fore draft and positive derived aft draft are both shown with
distinct source labels. The omitted beam stays unknown without defaults. An
attempt to overwrite the length with a conflicting same-ID form gets actual
409. Before and after disposing and opening a new SQLite Database object, the
original record, a single write audit event, and a valid case audit chain are
verified. A fresh Public read retains the dimension values and labels, cannot
edit, and another fictional case remains empty. No track, replay or dynamics
request is made.

## Why this does not add environment editing

At the same commit, [W9.2](../../contracts/W9.2-environment-observations.md)
explicitly limits the contract to GET and append-only POST. The environment
router and schema provide no update/delete, revision token, correction link,
or precedence/approved-input rule; duplicate IDs intentionally reject. A
same-ID overwrite or implicit latest-observation replay rule would violate
the fixed contract. To reopen the feature, the minimum product decision is
whether and how to create an auditable correction revision, preserve the
original and its per-record provenance, reject stale writes, and expose the
revision selection. Any replay integration also needs an independently
approved revision with an explicit time/location scope. A plain observation,
observed zero, or source label does not authorize dynamics.

This is not a browser acceptance, real account authentication, vessel data
certification, or simulation replay acceptance.

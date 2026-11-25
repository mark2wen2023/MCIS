# W11 opt-in local saved-graph / original-excerpt binding

A standalone synthetic test adapter only. No new service module registration,
public route, graph contract, default UI, archive, 4A, real account or real
investigation data. Each trial creates an isolated SQLite store for the same
one synthetic case, one edge and one synthetic original. The two stores
independently prove revision invalidation and explicit revocation.

The private singleton row is provisioned by the test host (not the caller)
and resides outside graph JSON. It binds the exact current case/revision/
digest, edge ID and both ends, registered evidence and intake identities,
source SHA, and UTF-8 byte endpoints. The host can only revoke, not change the
binding or reactivate it. The original-byte access and current graph/audit +
permission checks run in the same SQLite reserved-writer transaction using
existing server functions. No excerpt leaves that transaction unless the
existing Access commits successfully. Only the verified span is returned,
not the remaining file, recorded position, replay event, seek, or causal claim.
T+109 remains the source's written time with no clock interpretation.
The existing local role demo context is not production authentication.

Exact graph router/models are from `d9187fef1f979866ac4d8ce2064d1ac92f34bb36`
(blobs fc432a2934a6748f5f7cc6e87e9bbf28b50c8745 /
da82b921f8ab92e2473ff32f7b36fb472fa8a656). Remaining exact local
source tree is the registered-source replay stack: db90fdf7 intake, 871db66
custody reader, 7dfb326 scaffold. Existing `save_sync` persists the graph,
revision audit and request receipt and read side validates saved digests.
The actual .NET entry is not available here: a named fixture only replaces
the core result within the test. This verifies the real SQLite save/validate/
reload/auth/registered-byte functions, not real C# graph generation or one
integrated deployed source branch.

Use already available exact Git objects in one or more local clones (arbitrary
checkout state; no working file is consumed). Use an installed service virtualenv
and do not use Python -O:

```sh
/existing/venv/bin/python -I -B tests_acceptance/w11-excerpt-binding-local/run.py \
  --repository /existing/MCIS
```

The runner verifies all 186 files in SOURCES as exact Git blob IDs before importing
any service code. Repeat `--repository` if the objects are split across stores;
the runner cannot fetch. Alternatively use one or more `--source-dir /fixed/export`
arguments with fixed exported bytes. First matching relative path is validated
and mismatches fail closed, even if a later input also contains that path. The
runner materializes only pinned bytes in a temporary directory, then enters a
separate isolated Python process. `--verify-only` checks all the bytes without
starting the trial. It does not require being run from the repository directory.
The exact graphs/intake are from separate candidate revisions by design; this does
not claim a common production deployment.

Portability checked from /tmp using pinned local exports: full trial succeeds.
A wrong synthetic communication export exits 2 before importing the service;
a local clone missing source objects also exits 2 without fetching. The full
single-clone Git-object mode was not exercised here because no clone on this
machine contains all of the fixed objects. Actual Linux PASS at graph revision 1, saved graph and binding both
present after reopening, exact excerpt at T+109, wrong case/edge/role/absent
graph denied without Access, then separate graph revision and revocation
denials without Access before and after reopen. Each trial leaves exactly
Register + Access, a valid audit and no seek. No network or real model.

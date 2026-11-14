# Legacy registration serialization review branch

Coordinator authorized publication after local verification. Earlier no-push/commit statements
refer to the local-only stage. Sole intended parenta38d7485f2e2a50496d3c624de6ddcc081967720
is verified against remote safe-read-budget-preflight-review. One new commit only. Product
delta is restricted to legacy register_evidence: existing WRITE_LOCK and BEGIN IMMEDIATE
cover case/policy read, ID allocation, file write and DB commit. Aggregate research/product
budget changes are not included. Frozen product hash remains unchanged.

Actual self regression196 passed/2 missing-.NET skips; independent86 passed (overlapping
suites). Independent two-process shared-SQLite tests and real TCP before/after observations
are included. All fixtures are synthetic. Historical full baseline failures are not claimed
resolved or rerun by this narrower test set.

This fixes concurrent ID allocation/policy ordering; it does NOT implement aggregate memory
budgets, HTTP admission or bounded request buffering. Full writer locks and parsed-body
waiting remain. Filesystem/database crash atomicity and other database backends are not
established. Spoofable role headers, real authentication/source truthfulness and production
performance remain unvalidated. No automatic retry or unknown-commit outcome reclassification.
No private records, credentials or .env files included. No PR, merge or deployment.

# Isolated durable pending-readiness / shared access decision

Base68c3e4ae3215a9b30be2b0c3c028bf830daf9c4b. Not product wiring.
Persist waiting_publication alongside the actual restore business/commit
transaction in a separate research metadata table (not product Base). A claim
without readiness/commit still blocks; failure/unknown must not fall back to legacy.
No code can promote an operation to ready: the observer does not prove atomic
publication, immutable ownership, or all route isolation. Never treat a supplied
ready string as readiness authority. Existing inactive receipts remain inactive.

Legacy compatibility: no operation and no readiness record means proceed through
existing business/permission checks, NOT permission granted. An old SQLite DB
without either research table is likewise unaffected. Missing one record for an
explicit operation is hold. SQL errors are unknown errors, not an empty list or
legacy fallback. List filtering is only for explicitly identified held cases;
legacy normal cases are preserved. A database without any operation protocol
cannot distinguish a lost operation ledger from a genuine old database: production
migration will require a durable protocol version and corruption handling before
these rules can be used as a production gate.

Readiness checks and business reads must share a transaction/session. Research
wrappers exercise real case list/load; scoped_call demonstrates a guarded boundary
for services that bypass load_case, not an installed HTTP middleware. Permissions
are still the responsibility of the existing operation and never replaced.
No production listing or access behavior changes; no package becomes supported.

Pending row is atomic with restored data and commit marker. A claim is durable
before that transaction: rollback leaves the claim, hence hold even without a
pending row. There is no deletion, retry, auto-recovery, or active authorization.
Post-commit response loss is not genuine uncertain SQLite commit or process crash.

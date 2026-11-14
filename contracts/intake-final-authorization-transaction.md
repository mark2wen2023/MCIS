# SQLite final intake authorization transaction

Proposed isolated dependency port for main; no new endpoint/schema/identity system.
Inside evidence-intakes:commit retain WRITE_LOCK, create a fresh DB session, then call
existing reports.access.begin(s) BEFORE final authorize(write=True). This reserves a
SQLite writer through binding validation, existing-receipt replay or new evidence/
custody/audit writes, and transaction commit/rollback. Same two lines exist in upstream
aac3c50; its unrelated source-incarnation allocation is NOT included.

If revocation commits before this reserved transaction, final authorization sees current
policy and rejects403 without new records/blob. If intake reserves the writer first,
a different SQLite connection cannot commit revocation inside the check/write interval;
it may wait or receive SQLITE_BUSY, and proceeds after intake commit/rollback. This is
ordered authorization, not cancellation of an already authorized committed intake.
Subsequent replay/download still checks current permissions. No success/read is allowed
solely because an old preview was authorized.

Second-connection regression uses real SQLite, synthetic policy/case and deterministic
interleaving hooks. It proves DB transaction ordering, not production authenticated
identity or a remote attack. Local filesystem-mutator tests are separately labeled.
Existing rollback/file cleanup behavior remains; crash-atomic file+DB storage and
write-path directory races are NOT solved. This reservation helper is SQLite-specific;
no non-SQLite database concurrency guarantee or deployment is claimed.

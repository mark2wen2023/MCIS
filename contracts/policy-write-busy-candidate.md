# Policy PUT initial SQLite lock contention

Access-policy PUT reserves SQLite writer before case/policy reads and before writes.
Only a numeric SQLite BUSY/LOCKED OperationalError (including extended codes) from that
initial reservation, with no invalidated connection and successful session.rollback(),
returns503 POLICY_WRITE_BUSY with detail.commitState=not_committed, detail.retryable=true.
No policy/audit writes have run at that point. Role check and schema validation stay first.
No string-message matching, no automatic retries, no partial policy writes.

Errors later in the body/commit phase, unknown SQLite codes, other DB dialects, invalidated
connections, or rollback failure are NOT classified retryable/not_committed by this helper.
Existing generic500 is not a declaration of database outcome; clients must treat it as
unknown and inspect current policy/audit before deciding any further action. In particular,
a commit that succeeds then raises must not get503 or invite blind automatic retry.
For POLICY_WRITE_BUSY only, re-read current policy before deliberate retry; stale replacement
of an entire policy can overwrite concurrent changes. No automatic retry is implemented.

Initial BEGIN IMMEDIATE uses existing reservation proof, preserving audit lock order and
avoiding WRITE_LOCK acquisition while holding an unproven SQLite writer. Evidence-read
transactions, digest checks, revocation order and default busy_timeout remain unchanged.
No shorter lock coverage, throughput improvement, fairness/cancellation guarantee or deadline
is claimed. This is restricted failure semantics, not general database exception handling.

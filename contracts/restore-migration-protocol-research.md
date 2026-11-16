# Isolated restore protocol v1 — no product readiness

A deployment must retain an expected database identity outside the restore ledger.
Without it, loss of all protocol tables cannot be distinguished from a genuine old
DB. This research requires explicit legacy mode or an expected identity; it does
not guess mode from missing tables. Production configuration/migration is NOT wired.

Explicit activation runs once under BEGIN IMMEDIATE, captures existing ordinary
case IDs and inserts a singleton protocol version/database identity in the same
transaction. Activation refuses existing restore claims/markers: no retroactive
claim that an unclassified restored case was legacy. Repeated activation refuses.
Failed activation rolls back; caller must not assume commit failure from timeout.
Existing IntakeReceipt is unchanged, not replaced.

Existing operation claim/attempt/commit/readiness tables remain authoritative for
research restores. For a marked database, missing schema, identity/version mismatch,
unknown new case, orphan or inconsistent operation association is unknown/held.
Captured ordinary cases retain the existing policy path (not authorization).
An operation cannot become ordinary by dropping its readiness row. Deleting every
trace including external identity is outside this contract; do not infer integrity.

Publication phases: claimed -> attempted (durable before restore) -> database commit
observed with waiting_publication -> matching directory inventory observed. The last
state STILL is not ready. Missing commit after attempt is unknown, not rolled back;
missing/inconsistent files after commit require investigation. Responses lost AFTER
actual commit can be recognized by read-only reopening, but are not true uncertain
SQLite commits. No retry/delete/publish/promote API. Original source receipts remain
inactive history and registered hashes do not prove original bytes.

Next prerequisites: protected deployment identity/migration ownership, atomic normal
case registration, all product access gates, owned no-replace publication/durability,
writer exclusion and real crash tests. Until then product experimental import/export
refusals and authorization remain unchanged. Ordinary cases are not filtered in the
product. This protocol is implemented only on self-created temporary research stores.

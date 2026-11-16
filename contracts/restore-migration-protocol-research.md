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

## Research read entry strategy
load_case/list_cases/scoped_call in readiness_gate now accept expected_database_id
and explicit_legacy keywords. A present migration marker forces classify even if
the caller omits identity (unknown). Expected identity forces classify even when
all metadata is missing. Only unmarked, no-identity research callers retain the old
decision path for backwards compatibility; this cannot detect total metadata loss
without externally retained identity. Direct decision/product calls remain outside
these wrappers. Same session does not itself prove a SQLite snapshot; callers must
keep explicit transaction and existing policy for business operations.

Known pending cases are excluded from research listings; any unknown row or invalid
empty-store metadata raises ReadinessUnknown, never a successful incomplete/empty
list. A captured ordinary case remains individually readable under its original
policy even when another unknown case blocks a complete list. New ordinary cases
after migration are unknown until a future atomic normal-registration path exists;
this limitation prevents production deployment, not a reason to infer legacy.

Even when cases is empty, listing inspects IDs present in operation, commit and
readiness ledgers, not only their column shape. Orphan/inconsistent bindings raise
unknown. A well-formed empty store still returns[], as does a store containing only
consistent held claims; the latter means no visible cases, not no pending operations.

The ledger-ID check also applies to nonempty marked/expected-identity listings.
An unrelated orphan commit or readiness row makes the complete list unknown, even
if all actual case rows are classified ordinary. A consistent held claim does not
block listing ordinary cases. Individual case reads remain case-scoped; this is
not a global integrity certification, and unmarked legacy behavior is unchanged.

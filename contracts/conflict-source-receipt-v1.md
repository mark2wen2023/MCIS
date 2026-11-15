# Durable registry-only conflict source receipt (limited candidate)

POST /cases/{caseId}/conflicts/{conflictId}/source-receipts accepts exact
{expectedVersion,observations:{a,b}}. Existing timeline WRITE policy is required,
then current conflict token and full conflict schema are checked. For EVERY changed
side, both old/new evidence IDs must be nonempty and their same-case registrations
must pass existing interviews.access.source (full-content+visibility policy). Missing
reference/unknown digest409, denied/unregistered source403. No source byte reads.
Unchanged sides keep existing associations, including unknown history; not disclosed
or reclassified by this endpoint. No source visibility rule is broadened.

Server stores random UUID receipt, case/conflict ID, conflict token, proposed complete
a/b hash, self-reported actor/role, issued/expires UTC and source registry doc/custody
head/current SHA snapshot. Receipt expires after10 minutes, clock before issued time
also refuses. Returns same metadata with bytesVerified/humanReadVerified/
identityVerified=false. Preparation/return is not human reading or source authenticity.
Source snapshot uses entire custody head, so even intervening non-content custody
activity conservatively invalidates it. No refresh/reissue performed automatically.

Same-ID POST /conflicts consumes sourceReceiptId only when a/b changes. Existing
expectedVersion check runs first. No receipt retains409 guard. With receipt, all
source permissions are rechecked; receipt must match case/conflict/actor declarations,
expected version/proposed a+b, unconsumed and unexpired. Unknown/applicability409;
registry/custody mismatch412 includingABA. Preserve caller input, never silently
substitute newer registry. No receipt accepted for new record or unchanged observations.

BEGIN IMMEDIATE precedes reads; conflict update, audit, full revision with receiptId
and consumed_revision are one SQLite transaction. Failure rolls all back; concurrent
same-token submissions commit once, stale competitor412. Receipt issuance and its
conflict.sourceReceipt audit commit together in their own transaction. It does NOT
change conflict write token. No automatic retry after uncertain response/commit.
Persisted receipt survives app restart; consumed/expired rows retained for history,
no deletion/GC endpoint. Growth/retention operational policy not production-validated.
Separate ConflictSourceReceipt table added by existing create_all migration.

Existing PATCH(status/resolution) unchanged policy/behavior; ordinary users denied
full source access can still record handling notes. Legacy clients changing observations
without receipt continue conservative409; client self-supplied SHA is never accepted.
This is an opt-in API, not a claim the workbench source editor is implemented; current
web PATCH flow has no new requirements. External clients must preserve rejected inputs.
Old pre-journal history stays unknown. Legacy first receipted edit may bind the NEW
observation at current registry version, not its historic preimage. Sources/identity
are not independently verified. New-record original declaration semantics unchanged.

Conflict archives still rejected; new receipt table not added to any allowlist. Offline
archive experiments may need schema evolution for sourceReceiptId; no backup support
claimed. No production login, original-read receipt or human approval implemented.

# Research restore operation / read-only commit observation

Existing product IntakeReceipt persists successful import metadata and links source
ZIP by digest. It is not absent. The missing protocol binds operation ownership,
staging/publication, DB commit and readiness; this candidate implements only the
DB operation/commit observation prerequisite, not that whole protocol.

Owned research directory/database only. No caller-selected product destination, no
HTTP route or production schema registration. DurableObservedConflictStore reuses
TemporaryContinuingConflictStore business restoration. It retains its directory on
exit/error and has no destructor cleanup, automatic deletion, retry or recovery write.

claim validates exact experimental ZIP/hash, requires empty destination business
state and no prior operation, then stores server UUID, case, source SHA and attempts=0.
restore_claimed checks identity/exact input and durably sets attempts=1 before restoring.
Every subsequent attempt rejects, even if an earlier exception was a known test
rollback. No generic restore entry permits bypassing this operation within this API.

A commit marker is inserted inside the same existing restoration session/transaction,
after reconstructed archive validation and before commit. It binds operation, case,
source ZIP digest and revision/receipt counts. Historical receipts remain in the
inactive table. Ordinary restore rollback also rolls back this marker; the prior
operation claim/attempt persists. This does not migrate product IntakeReceipt.

observe opens a fresh SQLite mode=ro connection, query_only, explicit read snapshot,
and closes it. It checks operation/marker identity plus retained source ZIP digest,
case presence and empty active source-receipt table. Returns only:
- claimed_unattempted (no commit marker, attempts=0)
- unknown_no_commit_marker (attempted, marker absent; never automatically safe retry)
- db_committed_publication_unverified (matching DB transaction marker visible)
- unknown (missing/unavailable DB/operation, inconsistent evidence or query failure)
Every outcome sets restore_ready=false, retryAllowed=false, deleteAllowed=false.
Even dbCommitObserved=true is not product success/current-history integrity proof.
No file publication, ready transition, authorization, current state repair or import
rerun exists. Observation is not a cryptographic guarantee against a DB administrator.

Tests simulate lost response AFTER an actual completed transaction; this is not an
actual ambiguous SQLite commit failure, killed process, machine crash or power-loss
trial. Fresh subprocess read confirms persistence; it does not establish filesystem
crash durability. Source archives are still BLOBs, not published product originals.
Product experimental409/422 protections and normal case visibility remain unchanged.

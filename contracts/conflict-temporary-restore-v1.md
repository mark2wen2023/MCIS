# Disposable conflict restoration candidate v1

This contract covers only TemporaryConflictStore in conflict_sandbox.py. It is not
product import/export or a permission grant. It uses experimental envelope version
1.5.0-draft.conflicts.1; normal product intake/export refusal remains unchanged.
Constructor always creates a new owned TemporaryDirectory and SQLite database, cannot
accept a caller-supplied product DB/root. Context exit disposes and deletes that
explicitly disposable research store. No archive gets written to a product case path.

## Preparation and atomic transaction

restore(raw,expected_sha256=...) reruns the bounded envelope/member validation against
these exact bytes, then begins an SQLite IMMEDIATE transaction and requires every
target business/research table empty. Repeated or competing restoration is refused,
not treated as an authenticated idempotent request. No existing cases are overwritten.

Insert current conflict rows with exact key/doc/createdUtc/updatedUtc and every captured
revision with its original ID/ordinal/doc. Insert case/vessel/evidence documents and
policy, reconstruct audit/custody rows from original raw lines and preserve original
sequences, hashes, actor declarations and source associations. Append-only triggers
remain enabled. No conflict.add/update is replayed; no human approval is generated.
Unknown old history remains unknown, with absent prefix or first beforeSources=null.

All supplied members and exact source ZIP are retained in separate SQLite BLOB tables
in that same transaction. Research tables use their own SQLAlchemy metadata and are
not registered in the product models registry. A local receipt records source digest
and case ID; it is not an active product request receipt and is not exported as a new
business audit event. No original file is published/extracted into product layout.
Rebuild and validate the candidate from inserted database rows before commit. Any
normal pre-commit exception rolls back business rows, journals, audits and BLOBs.

## Re-export and preservation boundary

export_candidate reads one SQLite transaction, rejects unsupported populated tables,
checks stored source/member integrity and rebuilds case/evidence/current conflict/
revision/audit/custody data from restored database rows. It verifies exact source
snapshot equality for documents/journal and original raw audit line sequences, then
builds/validates an experimental ZIP manifest using actual output member digests.
Original raw evidence bytes are copied from transactionally retained BLOBs. JSON
formatting, ZIP metadata and manifest lastModifiedAtUtc may differ; conflict row
values/timestamps, captured revisions, original audit/custody line bytes, evidence
registration documents and packaged raw bytes are preserved. Case/vessel/evidence
ORM timestamps were not in this envelope, so newly generated ORM timestamps are NOT
claimed original. Conflict timestamps ARE exact.

This candidate is a frozen snapshot clone. Later edits are not supported: changed
business data or added unsupported states cause re-export refusal. It does not yet
support continued live investigation or multi-hop product import receipt lineage.
Source receipt/ZIP remain available locally, but are not added to the next experimental
package. Two restores preserve the business snapshot, not a newly invented import
history. Production restoration requires those separate contracts before enabling.

## Safety and acceptance limits

No product route/allowlist/parser/policy change. Existing history reader still applies
its permission rules when invoked against these rows; role declarations remain
unverified. No trusted SSO or current production authorization wiring is implemented.
Registry hashes and bytesVerified=false retain their meaning; current supplied byte
checks do not verify unavailable historical originals or source authenticity.

Fault injection is an explicit research-only parameter for five pre-commit checkpoints.
It is not exposed via any API. Tests establish normal exception rollback and writer
serialization, not crash durability, disk failure, uncertain commit or production load.
No automatic retries or compensating deletion of uncertain product objects occur.
Only controlled synthetic temporary stores are covered. Product export must continue
refusing conflict cases until independent end-to-end review and further integration.

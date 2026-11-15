# Temporary SQLite conflict continuation v2

Research-only context manager owns fresh TemporaryDirectory/SQLite. No supplied
application database/root accepted, no product route enabled. restore_ready=false.
Based on a812d38 frozen restoration with v1/v2 envelope selection and exact history
prefix preservation; still not a general-purpose editable case restore.

Restore revalidates exact ZIP/hash, inserts case/vessels/evidence/policy/current
conflicts/full revisions/raw audit/custody and source package bytes in one destination
SQLite transaction. Historical receipts go only into offline_conflict_inactive_receipts
(separate research metadata), preserving the whole inactive-history entry. Active
ConflictSourceReceipt stays empty. Input archival receipts never become replay tokens.

Only subsequent existing ConflictPatch description/status edits are supported. They
use existing domain authorization/CAS/revision/audit transaction. No source reassignment,
new conflict inventory, custody/registry change, other module or fresh receipt is
accepted for re-export. A nonempty active receipt table is unsupported state. No
production permission policies are changed or waived; tests use declared LeadInvestigator,
not trustworthy authentication.

Export reconstructs from database rows and preserved member bytes. It requires exact
imported revision prefix and first local preimage, original creation timestamp,
coverage, evidence/policy/other immutable rows and inactive receipts. Current conflict
must match validated terminal history. New revisions must be conflict.update and must
not contain a sourceReceiptId. Original audit lines remain an exact prefix; appended
audit must be matching conflict updates, and complete member validation checks chain
and revision linkage. Custody remains identical. Original source ZIP/member equality
is still checked; the old total-current-snapshot equality is replaced by these bounded
continuation checks, not removed without replacement. Output retains input v1/v2 profile.

Legacy absent history stays unknown-before-capture. Later PATCH captures known new
revision with beforeSources=null; no earlier revisions or source bindings invented.
Existing unresolved-source/member restrictions remain (no broadened archive support).

Fault hooks are ordinary exceptions at current/journal/inactive_receipts/audit/objects/
before_commit, inside the same SQLite transaction. Tests prove rollback for those
exceptions and after actual appended revision capture. This is not process crash,
unknown commit, cross-database transaction, filesystem publication or cleanup proof.
Source archives/raw members remain BLOBs in the owned research DB. No product file
layout, IntakeReceipt, cross-import lineage or readiness-gated product case exists.
The ability to append notes here must not be described as formally continued casework.

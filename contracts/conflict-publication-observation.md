# Isolated operation-bound publication observation

This research slice reads existing persistent operation/commit markers and files;
it does not publish files, authorize access, or set product readiness. Base
5c303df9a4f4e907ff03b78ad11de5c553047363, including prior d6dd764 observer.
Existing product IntakeReceipt remains unchanged. No migration or route wiring.

## Binding and decision rules

One read-only SQLite transaction reads operation ID, case, source ZIP SHA,
attempt count and matching commit marker. The retained source ZIP must match its
registered SHA, exactly one case row must exist, and the active receipt table
must remain empty (archive history is not authorization). Missing/unreadable or
inconsistent database evidence is unknown, never proof of rollback or success.

For this existing limited experimental archive subset, expected product files
are deterministically derived from that same source ZIP. The mapping mirrors
mcase.import_case's raw/* and evidence/* subset, excluding evidence/index.json
and /.keep; package_intake adds _package_intake/source.mcase. A research-only
_package_intake/operation.json binds operation ID/case/source SHA/layout version.
The case directory basename must match the persisted case. Exact regular-file
inventory, byte lengths and SHA256 values must match. Missing, extra, differing
or mismatched marker files yield db_committed_layout_unverified.

| Evidence | Observation only |
| --- | --- |
| No readable matching operation/commit evidence | unknown / unknown_no_commit_marker |
| Claimed, no attempt | claimed_unattempted; no inferred retry permission |
| Committed DB, absent/inconsistent files | db_committed_layout_unverified |
| Matching DB and exact isolated file inventory | db_and_layout_observed_not_ready |

Every result has restore_ready=false, retryAllowed=false, deleteAllowed=false.
No result hides or exposes a product case. Existing ordinary cases, policies and
experimental package rejection are untouched. Inspection writes no marker,
imports no data, retries no operation, and removes nothing.

## Proof boundary / remaining blockers

The filesystem is NOT an atomic snapshot with SQLite. This cannot establish
future immutability, directory ownership against concurrent local replacement,
no-replace publication, fsync durability, or product-ready status. Exact-file
matching is a limited observation, not original authenticity or human review.
No restricted file-race/security/ECFC probe was run. Only owned synthetic files
were read; no production roots or original evidence.

The marker is currently created only by test fixtures. There is no product
publisher or persistent ready transition. A complete publisher must bind its
manifest to the commit transaction and establish exclusion/durability, then
all case list/read/write/export/intake entry points must apply a selective
pending-case gate alongside existing permissions. Old normal cases cannot be
inferred unready merely because they lack these new markers. Working-record
attachments and broader product layouts are outside this limited mapping.

Reopening in a separate Python process tests persistence/read-only observation,
not a process killed during write. Failure injections are Python exceptions;
response-loss injection occurs AFTER actual commit. An unavailable DB test
checks unknown/no-action semantics, not genuine SQLite commit ambiguity.
Product restore remains blocked. Browser/production identity/real cases untested.

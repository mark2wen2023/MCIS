# Continued investigation restoration: current-stack compatibility blockers

Base70d751a1431bca57d2f4c76cc9762ec095f5a45c. Inspected historical prerequisite
commit a812d388b09d4b5648aec1c729aca2d86f78382e directly with git show, no cherry-pick.
Their common ancestor is be93cfa0d273bb9a0120c97f8ca2994643dcf51f. Current candidate
contains later registry receipts, conservative observation editing and exact revision
references; old frozen restoration does not. Remote main read:94d5e38.

## New executable evidence

Frozen upstream schema file: fixtures/a812d38-conflict-archive.schema.json;
Git blob69b6beccee181a08a9de7f89213c37f1e4d8ee27;
SHA256 3a8584f5412be4a8ae498fcdee82a0d88e7aa82f397d6d7b742f2860befffe7d.
It is code/schema only, not case data. Referenced conflict.schema/common.schema are
identical between a812d38 and this base (git diff empty). Fixture is outside runtime
schema discovery and does not change the product contract.

    cd service
    PYTHONPATH=.. .venv/bin/pytest -q tests/test_conflict_restore_current_compatibility.py

Final1 passed in0.23s: actual synthetic case and registry, ordinary source-receipt
issue/save routes, history read, old revision schema validation. Creation revision
passes; saved revision has sourceReceiptId and fails old additionalProperties rule.
The test asserts stored history is unchanged; never strips fields or recalculates
historical hashes. This is a reproduced incompatibility, not restoration success.
Initial harness run failed because its standalone schema registry lacked common
schema; replaced with existing local contract registry (no runtime code changed).
No full old parser/external archive execution was claimed.

## Exact blockers, beyond file copying

1. a812d38 TemporaryConflictStore stores source ZIP/members in its own SQLite BLOB
   tables, and _export requires current rows/journal equal original input. It does
   not create product case files, IntakeReceipt or conflict import mapping. Copying
   BLOBs into blob_dir and deleting equality checks would not supply provenance.
2. Its conflict schema rejects new sourceReceiptId; its _ALLOWED has no current
   conflict_source_receipts table. Current receipt documents contain case/conflict,
   expected version, observations digest, source registration/custody bindings,
   actor declarations, issue/expiry and consumed_revision. Preserving only the UUID
   loses linkage; restoring it as active grants replay semantics not authorized by
   an archive. Need a distinct archived-history representation and validation of
   revision/audit/receipt associations, preserving exact original declarations.
3. Current working_records_archive build expects actual case-relative
   _package_intake/source.mcase bound by hash/byteLength/case to IntakeReceipt, plus
   lineage and history/artifacts. Old conflict envelope rejects those members.
   Thus even a filesystem copy plus forged success receipt cannot re-export safely.
4. TimelineImportOrigin is event-specific; not a conflict revision provenance map.
   Need import operation UUID, case/conflict, archive hash, exact imported prefix
   revision/hash and current row digest at import. Later local revisions must append;
   original declarations and unknown-before-capture remain unchanged. Mapping must
   survive multiple imports, not mistake an imported Confirmed/Resolved label for
   new human review. New import audit is separate from preserved old audit prefix.
5. Existing package_intake commit_sync renames staged directory within SQLite
   session before commit; exception cleanup may remove published target. Static
   inspection only, no crash/race/permission probe. It does not provide the durable
   operation/ownership/ready-state evidence needed to safely classify unknown commit
   or protect new restore objects from uncertain cleanup. Do not reuse it as proof
   of cross-filesystem/SQL atomicity. Process lock is not cross-process ownership.

## Concrete next design and acceptance dependency

Choose product filesystem layout (not a parallel BLOB reader migration), with
server-owned immutable prepared case objects plus operation manifest. Prepare exact
source ZIP and members with checksums into an isolated owned directory; record
operation identity, intended case and source digest. Database import must include
all current rows, full captured revisions, raw audit/custody prefix, inactive archived
receipts and imported-prefix mappings in a single destination transaction. Keep
same IDs and hashes; source store is immutable input, not a cross-DB transaction.

Publication/recovery needs durable operation states and case access gates before
exposure: prepared / destination-committed-pending / ready / unknown. All supported
case readers/writers/export paths must respect readiness. A ready receipt requires
verified product layout/source ZIP/manifest plus committed DB associations. A
transaction exception is not by itself proof of rollback; reconcile uncertain state
against durable operation evidence, don't delete or automatically retry. Keep pending
objects until explicit ownership/reference-proven cleanup. Import actors and policies
must not create new privileges. Existing report/source permissions remain applicable.

This lifecycle is not implemented or verified here. Existing many case paths lack a
shared readiness gate, so a small new import handler cannot currently guarantee no
partially usable case. Implementing the gate and recovery protocol is a prerequisite,
not optional staging cleanup. No patch was made to broaden export/import acceptance.

Once these prerequisites exist, required tests are original/imported audit prefix
and source mapping across import->edit->export->import; all prior receipts inactive;
ordinary precommit injected rollback, pending/unknown reconciliation (no fake global
atomicity); genuine legacy unknown history; old supported package compatibility;
unhandled states still whole-package refusal. Browser notices then require actual
interaction acceptance. These are future tests, NOT results from this turn.

## Scope held

No usable product restore, revised export, injected rollback or old-package regression
was run this turn: the compatibility prerequisite failed before that stage. Earlier
three tests in a812d38 remain historical results, not rerun/current acceptance. No
original reads, credentials, real cases, LLM, restricted security/ECFC operations,
permission relaxation, merge or deployment. Browser/production identity unverified.
Only this assessment, frozen source schema and one synthetic diagnostic are added.

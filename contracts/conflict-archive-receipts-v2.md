# Offline conflict archive member v2 (not an enabled package version)

Scope: standalone member validator only; no product ZIP acceptance, export, database
restore or authorization. Runtime schema discovery/report contracts unchanged.
Implementation/schema live under research/conflict_source_intent, not product routers.

v1 remains exact a812d38 schema, unchanged, with original semantics. Version must be
integer1 or2. v2 extends the member with required receipts array and permits optional
sourceReceiptId on captured revisions. Existing revision format/hash remains exactly
as recorded: no field deletion, hash recomputation or invented legacy association.
The v2 schema is conflict-archive-v2.schema.json. v1 with new fields remains rejected.

Each receipt entry contains exactly receiptId, caseId, conflictId, consumedRevision,
authorization='inactive-history', doc (complete original server receipt document).
consumedRevision preserves null or recorded positive revision; even a null/unexpired
receipt is historical only. An importer MUST NOT insert these into the active
ConflictSourceReceipt table or pass them to accept(). No importer is supplied here.

Validation requires the full supplied same-case record/evidence/custody/audit sets.
Keep v1 revision chain, digest, before/after, actor, audit-line and source checks.
For v2 additionally require every conflict.sourceReceipt issuance event to have one
receipt and vice versa, same conflict/actor and bounded UTC interval; each consumed
receipt has exactly one matching revision and captured sourceReceiptId. Require
pre-edit conflictVersion (before/current+previous revision hash), after observations
digest, changed-side old/new reference union and after-source bindings to agree.
Custody anchors must exist with the declared version and no later than issuance.
All verification flags stay false. No original bytes are read or inferred verified.

Unused receipts preserve their digest declarations but original proposal bodies are
not available, so proposal contents are not independently reconstructed/verified.
Missing issuance/dependency, duplicate consumption, wrong source/version/actor/time,
unknown format and active-authorization labels reject. Input JSON bounded16MiB,
4096 total revisions/receipts, inherited dependency limits; no performance claim.

Legacy no-capture records keep unknown-before-capture with empty revisions. v1
limitations remain: historical unresolved referenced-source variants and absent
source registrations unsupported by its member contract are still rejected; no
fabricated values or widened acceptance to hide the gap. Full outer ZIP completeness
and original authenticity are NOT established by supplied self-consistent hashes.

Output is validated JSON history only, not a restore-ready object or a live receipt.
Product case exports/imports remain guarded. Whole old-package compatibility, outer
v2 profile, multi-hop import lineage, file readiness, transactional restoration and
continued-work roundtrip remain prerequisites before any product wiring.

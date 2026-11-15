# Forward conflict revision capture v1 (candidate)

Existing POST /cases/{id}/conflicts and PATCH /conflicts/{id} retain input/response
schema and timeline write authorization. Same-ID POST still replaces current data,
but now preserves full preimage/postimage. No automatic historical approval.
SQLite only: reserve writer before policy/current/source reads; current row, existing
summary audit, and append-only conflict_revisions row commit/rollback together.
No non-SQLite fallback. Concurrent writes are serialized, not optimistic client CAS;
last accepted update wins but every accepted preimage is retained. No auto retry.

A revision contains case/conflict ID, ordinal, complete before/after documents,
actor/role declarations, UTC, auditSeq and original audit-line SHA256, source bindings,
previous revision SHA and canonical full-document SHA. No400-character truncation of
snapshots. Digests are consistency checks, not signatures or protection against a DB
administrator. Actor headers remain unverified self-reported identity.

New records with no existing row/history start captured-from-creation. Existing rows
or prior audit with no journal start unknown-before-capture; first captured before is
only the current visible baseline. Earlier authors/versions/time are not invented.
Absent journal on read returns unknown-before-capture and no revisions. Existing
creation timestamps remain unchanged on upsert; revision UTC is the actual operation.
A current row inconsistent with last recorded postimage rejects409 before overwrite.

Per-observation afterSources records the current SAME-CASE evidence registry digest
and custody-head sequence/hash at capture, if available. It is a registered-version,
not proof the observation originally came from those bytes: bytesVerified=false,
no file I/O. Missing evidence is unresolved; absent ID is unregistered. Unchanged
observation keeps prior binding even if custody later changes. New/changed observation
captures the then-current registered version. An old baseline has beforeSources=null
because its original evidence version is unknown. Its first after binding refers to
capture time, not the historical creation date. No guessed historical association.

GET /cases/{caseId}/conflicts/{conflictId}/revisions is new, no-store. Requires existing
timeline access AND existing full-content policy, then rechecks referenced evidence
using the existing source gate, including historical preimages. This gate checks
same-case evidence registration existence and its visibility under the current policy.
Default Investigator is therefore403; LeadInvestigator may read permitted revision
metadata. Missing or policy-invisible evidence registrations fail closed; do not strip
history and claim complete. It does not open source files, check their existence or
readability, hash file bytes, or detect missing/modified original files. bytesVerified=false
remains false on history reads. Stored registry digests are not compared with returned
file bytes, and a successful history response does not certify source-file integrity. Digest,
revision sequence, preimage/postimage, case and audit binding are checked before return.
Existing conflict list/read behavior is unchanged; no frontend integration claimed.

Storage migration is additive create_all of one table with SQLite append-only triggers.
No old rows are rewritten/backfilled. Existing conflict archive refusal remains; the
new journal table is NOT whitelisted. This is a prerequisite for a future reviewed
archive format, NOT conflict backup support. Full evidence bytes are not snapshotted
here and later file availability is not guaranteed by the stored registry digest.

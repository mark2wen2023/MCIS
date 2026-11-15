# Conflict restore for continued investigation: prerequisites, not enabled

Base2acbb27bde7461d993da4c80bc2df40b38eb59fc; research branch
research/conflict-live-restore-prerequisites. Remote main checked this turn:
94d5e38c926fda232bb987b60fa9145e4bcf01a7. This assessment depends on the unmerged
experimental candidate stack. Only ordinary synthetic tests/docs; no runtime changes.

## Decision

Do not connect product restore/export yet. The journal/CAS domain functions can operate
on restored rows, but an editable, repeatably exportable case with durable product
files and import lineage is NOT supplied by the frozen SQLite sandbox. Merely removing
its equality check or broadening the product archive allowlist would discard the
missing guarantees. No safe small runtime change is justified by this evidence.

## Read-only findings and ordinary reproductions

1. `conflict_sandbox.py` stores supplied members and original ZIP in SQLite BLOBs;
   product readers use a case-relative filesystem under configured blob_dir. The
   research receipt is separate metadata, not `package_intake_receipts`. Tests confirm
   exact source bytes are retained, but no product case directory or intake receipt
   exists. This was checked by directory existence/DB lookup, not protected original
   GET, private-file access or a security probe.
2. Existing `timeline.router.patch_conflict` can append a correct revision and audit
   to the temporary restored rows under the existing policy and CAS. The test invokes
   actual domain route functions with a synthetic declared LeadInvestigator context,
   not HTTP/SSO. Existing snapshots remain an exact prefix; same-token concurrent
   calls yield200/412 and exactly one appended revision. Sandbox export then refuses
   because it is deliberately a frozen snapshot. This does not enable continued
   product work or prove continued-work export compatibility.
3. The content-derived expectedVersion is identical before/after a faithful clone.
   It is a row/revision token, not an import-generation identity, authenticated request
   or cross-instance replay guarantee. Future clients must reacquire context after
   restoration; whether a distinct import generation joins the token requires an
   explicit compatible contract, not a silent token-format change.
4. `package_intake/router.py:commit_sync` stages under blob_dir, writes/fsyncs source
   ZIP, inserts receipt/origin in SQLite, renames staged case directory to target,
   then exits DB session to commit. `WRITE_LOCK` is process-local; SQLite IMMEDIATE
   coordinates that DB's writers, not arbitrary filesystem writers or another DB.
   Existing exception code removes a published target. This is static architecture
   evidence, not a newly executed race/unknown-commit probe or a claim of a remote
   vulnerability. The module itself disclaims filesystem/SQL crash atomicity. Do not
   copy that cleanup into a new flow and assume it handles an uncertain commit.
5. `working_records_archive/service.py:build` requires a product receipt bound to
   `_package_intake/source.mcase`, and carries source archives through importHistory,
   historicalArtifacts and lineage. Experimental conflict envelope deliberately
   rejects those members. Its local receipt therefore cannot serve as the existing
   product provenance contract. Merely writing source.mcase alone is insufficient.
6. `timeline/origin.py` binds latest import/event row digest to its original package;
   it is not a generic conflict/revision origin registry. A conflict's captured audit
   is an original actor declaration, not evidence of new import review. There is no
   product mapping for a restored conflict's imported revision prefix/source archive.
7. `common/context.py` still accepts X-MCIS-Role and operator headers and defaults to
   Investigator. Existing permission policies remain necessary but do not authenticate
   identity. No SSO/real principal inference or permission relaxation is authorized.

## Required design, in order

### Storage and cross-resource boundary

Choose a canonical evidence-byte store before exposing the new profile. Two feasible
paths need separate implementation/review:
- Keep bytes in the same SQLite transaction (as demonstrated), but add authorized,
  bounded product read/export adapters for every relevant file consumer. Existing
  disk paths cannot simply point to absent files. This is a broader storage migration.
- Keep product filesystem layout, with durable import identity/state and immutable
  owned objects, exclusive publication, validated readiness and recovery before any
  case becomes usable. Pending/failed/unknown commit states require explicit outcomes.
  Process-local locks and one SQLite transaction alone are not a distributed commit.

For the filesystem path, define prepare/object-retention/DB-commit/publication/ready
states and gate readers/writers until ready. A durable operation ID must bind source
hash, target case, intended objects and DB receipt. Confirmed rollback may be reported
as failed; unknown commit must block retry until reconciled against durable evidence.
Never automatically delete or retry an uncertain object; garbage collection needs
explicit ownership and durable no-reference proof. Fsync/recovery semantics and
multi-process case claims must be tested normally in authorized scope before enabling.
This document does not implement or validate either option.

Cross-database restore must preserve case/key/revision/audit sequence identities, while
allowing local autoincrement IDs to differ. Reject a preexisting target case, source
policy mismatch or unsupported nonempty table; do not merge unknown existing state.
SQL schema/migration compatibility is required on every supported target. Do not claim
cross-DB transaction atomicity: source is an immutable validated snapshot, destination
has its own explicit commit/recovery outcome.

### Continued work plus original-source history

Define a stable combined profile (experimental tag remains unaccepted) that includes
original source archive objects, their hashes and lineage, exact imported conflict
rows/journals/audit prefixes, and local import provenance. Reuse existing archive-only
receipt semantics: old request receipts never become active replay authorizations.

A server-created import binding should identify case/conflict, package SHA and exact
imported row/revision prefix. It must survive subsequent edits while clearly marking
which revisions predate this import and which are later local actions. A genuinely
legacy unknown prefix stays unknown. Do not infer origin from dates/status or replace
old actor declarations. Subsequent edits must extend the captured chain and existing
CAS/audit transaction; export validates the full journal and imported-prefix binding,
not just equality with an immutable initial current row. Record new import activity
separately, never as a renewed human confirmation. Latest timeline-event origins and
future conflict origins must coexist without conflating them.

Version history can preserve registered digest declarations without possessing old
bytes. Missing historical originals must remain explicit and bytesVerified=false;
only included actual bytes may be checked against their registered hashes. Current
outer reader still rejects replaced-original histories; that restriction cannot be
removed solely because the journal can name a hash.

### Permissions and concurrency

Retain current server policy gates at read, write, export and import/recovery; perform
historical-source checks for all before/after references, not just the current record.
Use existing reserved SQLite transaction for the policy/source snapshot, preserving
revocation ordering; do not release it just to optimize file I/O. True identity and
case membership must be resolved before any production-security claim. Untrusted
imported policy/actor fields cannot grant new privileges. Existing supported policy
restrictions stay in place.

Serialize destination claims across processes, not only this worker's threading lock.
Define refresh/reselection semantics when a case is reintroduced in a different store;
old UI buffers are not proof of a current authorized editing session. No automatic
retry of412/428 or unknown commit. Existing header/case limitations remain explicit.

## Minimum ordinary acceptance before a product candidate

- A→B→C captured revisions and legacy unknown prefix: export/restore, continue with D,
  export/restore again; exact original audit prefix and all revisions/source bindings
  preserved, local import and later actors clearly separated, old receipts inactive.
- Product file paths/read adapters and raw-byte retrieval tested under existing allowed
  permissions; retained original package and multi-hop lineage verified without
  inventing unavailable originals. Do not run any previously restricted probe.
- Ordinary injected pre-commit failures: no visible case/partial journal/files; recovery
  state documented for post-commit/pending cases. Crash/unknown-result guarantees need
  explicit separate authorized evidence, not extrapolation from exception rollback.
- Same-ID concurrent claim/edit and source policy changes keep existing semantics;
  other cases remain isolated. Normal existing formats1.0/1.2/1.4 and bounded1.3/1.1
  when real dependencies exist must retain their contracts. No fake SDK/core success.
- Every unhandled business state/combination still refuses the whole package.
  Browser review of restored-history versus current-review notices is still required.

## Actual tests this turn

`service/.venv/bin/pytest -q service/tests/test_conflict_live_restore_prerequisites.py`
3 passed in0.94s. Actual existing domain functions plus temporary SQLite, synthetic
case and declarations. Tests establish append/CAS behavior and the concrete frozen
export/product-layout gap only. No runtime files changed; no real HTTP/browser/SSO,
crash/unknown commit, raw-original permissions or production validation. Earlier145
expanded and2 targeted tests belong to the parent and were not rerun. No deployment,
merge, push, restricted historical-security/ECFC or protection query was performed.

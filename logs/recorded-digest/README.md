# Recorded-digest delivery research candidate

Base ee6071f2159baa2510ba31c2cb17d090a8b082f1. Review branch
codex/recorded-digest-delivery-review. The parent authorized publishing this isolated
candidate for independent coordination review. No merge or deployment; main and earlier
review branches remain unchanged.

## Finding and trust boundary

Evidence registration with contentBase64 calls write_blob and records its computed SHA256
in EvidenceRow.doc.sha256 and a Register custody row. Registration with sha256 alone accepts
a declared digest; package import similarly imports supplied records. The schema does not
store digest provenance. Thus not every existing digest can be called a server-observed
original digest. This proposal assumes SQLite records and application process are trusted,
while a local actor can change blob files; it is not protection against DB/process compromise
and does not establish remote modification capability or source authenticity.

before.txt reruns two prior endpoint probes on ee6071f: after-open overwrite still delivered
changed bytes. audit-baseline.txt/test_digest_audit_probe.py separately reproduce GET200:
response SHA matches modified bytes while successful Access SHA equals original recorded
SHA. Legacy export regenerated manifest is self-consistent but not proof of registered bytes.

## Proposed minimal behavior

Three product files: evidence/recorded_content.py, evidence/router.py, package/mcase.py.
No descriptor helper change, schema migration, new endpoint or cryptographic dependency.

- Pin policy/item/events under SQLite BEGIN IMMEDIATE for GET; legacy export already holds
  its reserved transaction. Existing permissions precede content reading.
- Reference starts at recorded item.sha256. Require64hex, normalize case, reject conflicting
  Register digest. Each Change must reference the preceding digest and supply a valid next
  digest. Verify/Access events do not redefine it. A valid Change authorizes comparison to
  current recorded version, not a claim of matching original bytes.
- Read via prior no-symlink reader, hash the exact immutable bytes that will be returned or
  put into ZIP, and compare to the pinned reference. Never substitute a recomputed hash
  for missing reference or verify a later second read of disk.
- Reject409 EVIDENCE_DIGEST_UNAVAILABLE / EVIDENCE_DIGEST_CONFLICT /
  EVIDENCE_CONTENT_MISMATCH for missing/malformed/conflicting/mismatching records/content.
  No successful Access/export event commits on refusal. On successful GET, Access digest,
  response X-Sha256 and SHA256(response bytes) match the verified recorded current version.
- Existing valid-digest missing file404/legacy omission remains. Invalid-digest record now
  refuses even if file is absent. That stricter compatibility decision is explicit.

Concurrent reads need not be atomic filesystem snapshots: mixed bytes are rejected unless
matching the pinned reference under SHA256 collision-resistance assumption. Mutation after
read cannot alter immutable response bytes. This verifies delivered memory content, not
filesystem immutability or absence of attempted tampering. A later request can fail while
an already verified original snapshot remains valid to return.

## Legacy migration proposal, not executed

Keep original metadata, custody and files. Missing/malformed/unverifiable records require
manual integrity review; do not silently fill digest from present mutable disk contents.
Recover reference only from separately trusted original/independently verified historical
record with documented provenance and approval audit. Without an anchor, keep delivery
blocked. A future explicit unverified-copy workflow requires a separate contract/label.
Valid declared/imported digest records remain usable as recorded-digest matches, not labeled
source-authenticated or service-observed originals. Existing schema cannot infer provenance.
No old digest/history/audit row is rewritten. Historical misleading Access rows remain.

## Tests / artifacts

Initial focused run exposed two obsolete acceptance expectations of200 after
mutation: the initial local focused run had41 passed/2 failed. Existing tests are updated to the new409
contract, not removed; independent old-probe assertions likewise retain their baseline note.
Final counts are recorded below. New tests include after-open mutation,
mixed read followed by disk restoration, post-read mutation retaining verified original,
missing/malformed/missing-field digest, valid/broken Change transitions, actual SQLite
second-connection reservation, declared-only digest caveat and response/Access agreement.
Independent additional tests/report are under tests_acceptance/recorded-digest and DEFECTS.

Broader HFACS_CORE_UNAVAILABLE failure and missing.NET skip remain; no browser, Windows,
real intranet/model or deployment tests. No combined61/64/69 test here. Other read/write
paths, aggregate memory, provenance authentication, hardlinks/mount protection and process
or database compromise remain outside this local candidate. All probes use synthetic
fixtures and controlled local hooks; none demonstrate remote file mutation.

Final executed results:
- regression-final.txt:159 passed,1 existing HFACS_CORE_UNAVAILABLE failure,1 .NET skip,
  44.62s. Command from service: .venv/bin/python -m pytest -q -rs
  tests/test_recorded_digest_delivery.py tests/test_legacy_safe_delivery.py
  tests/test_evidence.py tests/test_contracts.py tests/test_package.py
  tests/test_archive_export_safety.py tests/test_package_zip_boundary.py
  tests/test_working_record_archive.py
- Independent51 passed/0skip in11.67s:10 new independent+12 prior descriptor+29 implementation
  digest cases. Counts overlap; do not sum. See DEFECTS/recorded-digest.md and acceptance log.
- Current product hashes are frozen in logs/recorded-digest-impl-hashes-frozen.txt.
- Holding SQLite writer reservation over legacy unbounded reads serializes other writes;
  operational performance on large files/multiple workers is not quantified. No integration
  release recommendation until compatibility/migration and contention are reviewed.

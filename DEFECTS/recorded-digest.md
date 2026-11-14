# Recorded-digest delivery candidate — independent local review

2026-11-14. Isolated tree /workspace/mcis-digest-review based on ee6071f.
Reviewer changed only acceptance tests and this report; no product edits, commits, push,
merge or deployment. Earlier descriptor-only branch/tree remains unchanged.

## Executed tests

From service/:

```sh
.venv/bin/python -m pytest -q --import-mode=importlib \
 ../tests_acceptance/recorded-digest/test_independent.py \
 ../tests_acceptance/legacy-descriptor-read/test_independent.py \
 tests/test_recorded_digest_delivery.py
```

**51 passed in11.67s**, no skipped cases. Includes10 newly independent cases,12 descriptor
acceptance cases (two post-open mutation expectations explicitly adapted to the new
contract), and29 implementation digest cases. Do not sum these again into broad coverage.
Actual output: tests_acceptance/recorded-digest/results.txt. Product SHA256 snapshot:
tests_acceptance/recorded-digest/product-hashes.txt.

New independent evidence uses isolated SQLite and synthetic2MiB+19-byte data with real
registration/GET/export APIs. Controlled OS read hooks actually modify the same inode
while reading; no model/network/intranet/production identity is involved.

- Mixed read: retain first original chunk, replace remaining on-disk bytes, then restore
  complete original disk contents at EOF. Both endpoints reject409 EVIDENCE_CONTENT_MISMATCH,
  even though a later reread would find correct disk contents. No success custody/audit.
- All changed bytes read, then original file restored at EOF: same rejection and rollback.
  These probes show verification binds the returned memory snapshot, not a second disk read.
- Two valid chained Change events, including uppercase SHA strings, permit current-version
  bytes. GET digest reflects those exact bytes. This preserves lawful current-version
  transitions, not just original-byte comparisons.
- Conflicting extra Register and absent item.sha256 are rejected before file read on both
  paths, with no success audit/custody.

Descriptor acceptance rerun retains parent substitution, fd cleanup on read failure,
permission-before-open, unsupported platform behavior. Only its two original post-open
mutation assertions changed from expected200 to409 in THIS isolated candidate, with an
explicit historical explanation. Prior branch baseline tests/results were not rewritten.

## Assessment and limits

No blocker found within the stated narrow local-record consistency contract. Suitable for
continued local review; this is NOT release/integration/deployment authorization.

The trusted SQLite/process premise is essential. Digest-only registration and imported
records can provide declared hashes; current schema does not establish hash provenance.
This candidate proves snapshot consistency with the recorded current digest, not source
authenticity, service-observed original acquisition, or signature validity. It assumes
SHA256 collision resistance and a valid trusted Change history. Custody row/line divergence
or forged trusted database records are outside this trust model.

Filesystem remains mutable, read allocation unbounded in aggregate, and other endpoints
(including explicit Verify) are not converted to this delivery guarantee. Candidate takes
SQLite writer reservation while GET reads, so performance/concurrency costs for large
files remain unmeasured. Missing/malformed metadata now intentionally blocks delivery;
this is a proposed behavior change requiring contract/migration review, not universal
legacy compatibility. Historical absent local file omission remains conditional on a
valid recorded digest. No automatic digest backfill from mutable disk should be performed.

No .NET/browser/Windows/full-system acceptance or PR61/64/69 combination was executed
by this reviewer. Existing broader baseline failures/skips remain separately recorded by
implementation agent; the51 passing cases do not erase those limitations.

# Legacy GET / package descriptor-read independent review

2026-11-14, independent agent legacy_independent. Reviewed local candidate on
cb04aa68d705bd77b04aaa19777395dd75f3fb51; no product edits, commits, remote changes,
merges or deployment performed by reviewer. Read AGENTS.md and stage handoff.

## Executed evidence

From service/:

```sh
.venv/bin/python -m pytest -q --import-mode=importlib \
  ../tests_acceptance/legacy-descriptor-read/test_independent.py \
  tests/test_legacy_safe_delivery.py
```

Result: **33 passed in 5.59s**, no skips. This includes12 independently authored
cases plus21 implementation cases; counts must not be added again to broader suites.
Output: tests_acceptance/legacy-descriptor-read/results.txt.
`sha256sum -c logs/legacy-descriptor-read-impl-hashes-frozen.txt`: all four product
files OK after test completion. Reviewer changed only acceptance files and this report.

Independent fixture creates an isolated SQLite database and synthetic case; uses real
legacy evidence registration and real TestClient GET/export endpoints. No external
service, model, intranet, or browser is used. Controlled OS hooks simulate a local
filesystem mutator; no remote actor capability is assumed.

Independent checks:

- Parent swap immediately before descriptor open (not a blob_path mock): both endpoints
  reject409, and neither custody nor audit receives a successful event.
- Synthetic os.read failure on the exact content inode:409, file fd closed, DB events
  rolled back, both endpoints.
- Public role denied before source descriptor open, both endpoints.
- Missing O_DIRECTORY and missing dir_fd capability:503 EVIDENCE_SAFE_READ_UNAVAILABLE,
  no new custody/audit events, both endpoints.
- Controlled same-inode overwrite AFTER source fd open: both endpoints still deliver
  changed bytes. GET X-Sha256 and regenerated export manifest describe those actual bytes;
  explicit Verify still reports mismatch with registered/current custody digest.

Rerun implementation21 cases additionally covers: original bytes and digest, missing
GET404 / missing legacy export member omission, symlinks, FIFO/directory, O_NOFOLLOW
absence, already-open parent directory pinning, access denial, chunk-size bound and
explicit mismatch verification. These reruns are distinguished from independently
written probes above.

## Verdict and retained KnownDefect boundaries

No new blocker found for the narrow descriptor-read candidate proceeding to remote
review. This is not attachment-integration approval or merge/deployment authorization.

**KnownDefect / explicitly out of scope:** descriptor pinning does not freeze inode
contents. Independent post-open mutation above actually reproduces this limitation.
The candidate does not compare delivered bytes with registered digest. A valid regenerated
manifest or X-Sha256 is not original-evidence authenticity. Existing explicit Verify is
not removed or weakened. Legacy missing-file omission remains unchanged.

Large legal files are not newly rejected by arbitrary size limits. <=1MiB read chunks
bound each read request, NOT total memory; sys.maxsize still permits in-memory accumulation.
Hard links, mounts, write-side races, other readers (including verify_one), production
identity, multi-process integration, Windows and browser acceptance are not established.
POSIX O_DIRECTORY/O_NOFOLLOW and dir_fd capabilities are required; missing support fails
closed rather than falling back.

Broader implementer records retain baseline HFACS_CORE_UNAVAILABLE failure and missing
.NET skip; reviewer did not rerun those broader suites or claim them independently passed.
Current candidate has not been tested combined with PR61/64/69 here; preserve PR64's
transaction/container permission gate when resolving its evidence GET overlap.

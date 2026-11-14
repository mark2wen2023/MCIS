# Legacy evidence GET / package descriptor-read review

Base: cb04aa68d705bd77b04aaa19777395dd75f3fb51 (safe-read/intake-authorization prerequisite).
This branch adds only legacy delivery follow-up code, tests, contracts and review records.
No #61/#64/#69 implementation or unrelated PR56 changes are included. No merge/deployment.

## What changes

Four product files,27 additions5 deletions. Evidence GET and package.build_files use the
shared descriptor-relative reader through evidence.safe_content. Shared reads request at
most1MiB per os.read so legacy sys.maxsize allowance does not request huge allocations.
This does NOT bound aggregate memory. Existing limited callers retain their byte limits.
Missing GET remains404; missing legacy package file remains omitted. Unsafe/special path409;
unsupported O_DIRECTORY/O_NOFOLLOW/dir_fd503 without fallback. Permissions remain first.

## Reproduction and integrity scope

before-clean-case.txt is the actual pre-fix failure: two safety assertions failed because
GET and legacy export returned synthetic bytes from an outside temporary directory after
local parent substitution; four normal/missing controls passed. Uses a new synthetic case,
actual registration and real TestClient routes; only the deterministic race hook is simulated.
No remote filesystem-mutator capability was established. A previous seeded-demo fixture
was blocked by its archive guard and was not used to support this finding.

Existing GET X-Sha256 and export manifest hash the actual bytes; neither compares against
the registered digest. This branch preserves that behavior. Explicit Verify still detects
registered digest mismatch, tested after an in-place modification. Valid manifest hashes
are not proof of unchanged original evidence. Missing legacy blob omission is also retained.

## Reproduce

From service, using .venv/bin/python:

```
.venv/bin/python -m pytest -q -rs tests/test_legacy_safe_delivery.py tests/test_evidence.py tests/test_contracts.py tests/test_intake_descriptor_read.py tests/test_intake_descriptor_independent.py tests/test_archive_safe_read.py tests/test_archive_read_independent.py tests/test_package.py tests/test_archive_export_safety.py tests/test_package_zip_boundary.py tests/test_working_record_archive.py
```

final-regression.txt:161 passed,1 existing HFACS failure,1 missing .NET skip in40.62s.
Earlier same-code split runs:
30 passed/1 .NET skip; package-reader-regression.txt131 passed/1 HFACS failure.
package-reader-baseline.txt runs the identical latter suite on cb04aa6:131 passed/1 same
HFACS_CORE_UNAVAILABLE failure (test_report_versions_full_review_gisis_and_hfacs_coexist).
These overlapping counts are not summed as unique coverage. No failed tests removed.
Independent acceptance tests/report are in tests_acceptance/legacy-descriptor-read and
DEFECTS/legacy-descriptor-read.md; their claims are limited to executed cases.

## Boundaries

Linux/POSIX capabilities required. Windows, actual browser, .NET and production identity
are not validated. No new combined #61/#64/#69 run; eventual integration must preserve PR64
container permissions and transaction lock. Other readers, notably verify_one read_bytes,
remain outside scope. In-place changes to pinned inode, hardlinks/mounts, writer races,
crash consistency, and total memory limits are unresolved. No integration/release approval.

Independent run:33 passed/0 skipped in5.59s (12 new acceptance cases plus21 implementation
cases), product hashes unchanged. Narrow candidate may proceed to review; no integration
approval. Actual after-open same-inode overwrite remains reproducible, documented in DEFECTS.
Raw pytest traces retain their original trailing whitespace; source/contract diff check passes.

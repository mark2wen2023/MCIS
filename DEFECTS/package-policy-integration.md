# Independent revalidation: policy repair in new main-based combination

2026-11-14. New isolated tree /workspace/mcis-main-policy-integrated; HEAD is actual main
3aba2bf03e393909c611489ae573a887087637ac with local staged combination and repair delta.
Original blocked tree /workspace/mcis-main-safe-integration remains unchanged. Reviewer
made no product edits, commits, push, merge or deployment.

## Actual execution

From service/:

```sh
MCIS_BLOCKER_OUTPUT=/workspace/mcis-main-policy-integrated/tests_acceptance/package-policy-integration/resolved-blocker.jsonl \
.venv/bin/python -m pytest -q --import-mode=importlib \
 ../tests_acceptance/main-safe-attachment-integration/test_plain_policy_blocker.py \
 ../tests_acceptance/main-safe-attachment-integration/test_independent.py \
 ../tests_acceptance/package-export-policy/test_independent.py \
 tests/test_package_export_policy.py
```

**52 passed in10.64s**, no skipped cases:
-2 original independently failing plain-policy blocker regressions;
-10 prior independently authored combined attachment/security cases;
-13 independent package-policy cases, including retained TrackPointRow binding regression;
-27 implementation policy cases.

Results: tests_acceptance/package-policy-integration/results.txt. Resolved-blocker JSONL
records actual mcis_service module path under this new tree, and both evidence_meta/audit
cases now show individual_status403 and export_status403. The original expected-denial
assertions were rerun unchanged; no xfail, deletion, mock denial or softened assertion.
Product hash snapshot is product-hashes.txt in that same directory.

## Integration inspection

The actual combined export ordering preserves all layers:

1. Existing reserved SQLite writer begins before new target-policy preflight and scoped
   record checks. Per-source/report/interview/recommendation/history gates remain.
2. build_files reads/validates immutable bytes against recorded current digests.
3. Existing PR64 integration protect_container scans those exact member bytes for ZIP-like
   content before delivery, retaining conservative full-content permission requirement.
4. New members() classifies/authorizes emitted original paths, including HFACS handling;
   only then are manifest and final ZIP constructed. No gate replaces another.

Individual evidence GET still retains descriptor-safe digest verification followed by
container gate before successful Access. Restored filename/hash/current policy and inactive
receipt behavior remain in the combined test. Ordinary allowed files still export; original
and prefixed ZIP cannot bypass individual/container permissions through whole export.

The52-case run also verifies no successful audit on denied/tampered/error paths, normal
read levels, scoped binding refusal including TrackPointRow, late member refusal rollback,
actual second SQLite connection blocked during final member check, revoke-before-reservation
and concurrent revoke/next-request behavior. It does not claim all possible policy matrices
or future serialized member types have been exhausted.

## Historical BLOCKED finding retained

DEFECTS/main-safe-attachment-integration.md remains byte-for-byte equal to the report in
original blocked tree. Both SHA256 values:
a050290c5462f1117a4dacd41c7bef9972c669196cb8e99b4f140b36aaa31e43.
It correctly records the prior defect inherited from pristine main. Historical baseline and
failure outputs were not edited or removed. This new report records local closure in the
NEW repaired combination only; it does not retroactively declare old main/candidate safe.

## Current bounded conclusion

Original evidence_meta/audit plain-file export blockers are resolved by the current local
repair in this inspected combination. No new blocker found in this52-case independent
revalidation. This is not authorization to push/merge/deploy or blanket full-system release.

Header roles remain unverified identity; policy consistency is not production authentication.
Database/process trust, metadata/category/provenance limits, aggregate memory and long
writer-lock costs remain. NonZIP content is not generalized report/PII classification.
HFACS baseline failures, .NET skips, browser limitations and whole-suite outcomes must stay
in coordinator's final report; this focused run has no such skips because it did not run
those broader tasks. No browser save, .NET, remote exploit, full platform/performance or
all-endpoint security acceptance was independently established here.

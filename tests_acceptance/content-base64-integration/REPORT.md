# Local composition of content visibility and Base64 fixes

Worktree:/workspace/mcis-content-base64-integration
Local branch:local/content-base64-integration
HEAD/base:099185719d01e31e440b3473310f30a3aa74157a (unchanged, no new commits).
Sibling inputs:f3957e3ae110d6dd6e1eeb5b62133e16e24ed1ef and
70f7067e8831a4d79eff8f613b7e45f349cc9b0c. Neither sibling includes the other.

## Composition

Applied both single-commit diffs to the common parent without importing histories or
creating a merge commit. Product diff only touches service/mcis_service/evidence/router.py:
strict canonical Base64 decode before POST writes, and filter_evidence before GET content
read/Access audit. Git3-way applied these distinct regions cleanly. Shared REQUESTS/ROADMAP
append-only additions were checked against common base and both retained explicitly.
No other product changes. composition.json records source commits and composed hash;
new logs/content-base64-integration-impl-hashes-frozen.txt records the combined router.
Historical standalone hashes/reports remain intact and refer to their own source versions,
not the newly composed file. Exact expected composition was checked programmatically.

## Verification scope

Two new end-to-end cases use empty bytes and nonUTF8 binary: malformed Base64 rejects422
without filesystem/database/audit writes; valid registration stores exact digest/bytes;
restricted Remove then denies content and export without Access records; Lead exports and
restores into empty service; restored Investigator remains denied and Lead gets exact bytes.
Recorded source metadata and audit/custody hash chains survive. Synthetic fixtures only,
no private records or model services. This checks preserved declarations, not origin truth.

Independent focused run:23 passed in5.16s, no skips. It includes original source/restore
GET failure probes, case separation and SQLite concurrency, Base64 loopback HTTP and
no-overwrite/empty/binary cases plus new combined workflows. Separate independent report
and evidence live in tests_acceptance/content-base64-integration-independent/.

Expanded regression command (from service/, with --import-mode=importlib) uses all suites
from the prior537-pass combination plus test_content_base64_integration.py,
test_content_visibility.py, test_package_policy_roundtrip.py and test_legacy_evidence_base64.py.
Actual new results are appended below and are not summed with focused overlapping runs.

## Retained semantics and limits

The original complete write transaction remains. A revoke committed before reservation is
seen; a concurrent policy writer blocked by an earlier read has not revoked access yet.
Known-safe reservation failures retain503/not_committed semantics; unknown commit results
are not reclassified for automatic retry. Digest, ZIP/DOCX and archive gates remain intact.
No performance improvement or memory-bound guarantee was introduced or measured here.

Role headers are spoofable and not SSO/authenticated identities; this is existing policy
consistency only. Offline backups retain snapshot policy, not future source revocations.
Expected SHA for dual-input POST is still a proposal: supplied SHA is ignored with content.
No browser/production/intranet acceptance, .NET availability or all-endpoint security claim.
Historical baseline failures and actual skips remain visible. No new commits, remote push,
PR, merge or deployment in this integration task.

## Actual expanded result

594 passed,5 failed,2 skipped in142.82s. Exact command is run-regression.sh; output is
regression.txt. Failure names were mechanically compared with base0991857 stored
logs/main-package-policy-review/integrated-backend.txt and are the same five:
- test_report_versions_full_review_gisis_and_hfacs_coexist (HFACS_CORE_UNAVAILABLE)
- test_interview_list_summary
- test_redaction_by_role
- test_crosscheck_requires_confirmation
- test_statement_add_and_review
The two skips require existing .NET SDK (evidence intake and evidence compatibility).
No newly failing tests in this compared scope; not a fully passing baseline or release.
Frozen product hash checked again after the run.

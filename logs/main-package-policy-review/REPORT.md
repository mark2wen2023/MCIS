# Legacy whole-case export policy consistency repair and re-integration

2026-11-14. Original inherited plain-export blocker is now locally closed by unchanged
expected-denial tests. No commits, pushes, merges or deployments. Not production authorization.

## Worktrees and scope

Independent repair: /workspace/mcis-package-policy, local/package-export-policy, base
13231d4067ce839775c0d47ecc30655c481aa1c0. Two product files: new package/access.py and four
mcase.py integration lines. Existing protected transactions/readers are unchanged.

New combined tree: /workspace/mcis-main-policy-integrated,
local/main-package-policy-integration, HEAD remains real main
3aba2bf03e393909c611489ae573a887087637ac. Applied the prior selected six single-commit deltas
cb04aa6/ee6071f/72269e3/13231d4/PR61aad96d4/PR645d10b67 plus previously reviewed legacy ZIP
export gate, then this independent repair. No97-commit/PR56 stack, PR69 or low-lock research.
Original blocked tree /workspace/mcis-main-safe-integration was NOT modified. Its BLOCKED
report and failure evidence are retained byte-for-byte in the new tree as historical records;
DEFECTS/package-policy-integration.md records the subsequent fixed result.

## Server-side checks

Before any blob read, within existing SQLite BEGIN IMMEDIATE:
- Read target case's stored policy; absent policy uses existing defaults, malformed/empty
  stored policy rejects instead of silently using defaults.
- Always-emitted raw categories ais_sim/evidence_meta/audit/timeline/recommendations/
  agent_drafts require ReadOnly or ReadWrite. Redacted is insufficient for a raw backup.
  Applies even to empty index/audit arrays, so empty history cannot bypass a policy.
- Validate scoped document caseId where present, including TrackPointRow; evidence must
  explicitly bind to target case. Do not redirect permission lookup through embedded IDs.
- Each evidence item passes existing filter_evidence visibility; Restricted requires full
  testimony level and VDR additionally requires full vdr_audio. A hidden item rejects the
  whole backup, not silent omission/partial export.

Before creating the legacy manifest/ZIP, every emitted original member maps to its category:
case/vessels/tracks/environment→ais_sim; evidence/raw→evidence_meta;
audit/agent/custody logs and included policy→audit; timeline/alignment→timeline;
COLREG→colreg; recommendations/consultation→recommendations; agents→agent_drafts;
testimony→testimony. Empty .keep markers carry no content. Unknown member fails409.
HFACS retains full-content gate. Existing report/interview/recommendation source/event/
per-draft protections stay in place. Working-history export retains its stronger full-content
and source/restore validation; it does not use the permissive legacy member path.

In the combined tree: descriptor-safe recorded-digest read -> container gate on SAME bytes
-> member policy gate -> manifest/ZIP. Historical filename restoration and same-case binding
remain. No UI-only hiding, client-supplied policy override, hash recomputation as proof of
originality, or shortened writer-lock scope.

Denial403 PACKAGE_CONTENT_FORBIDDEN; bad binding409 PACKAGE_CASE_BINDING; unclassified
member409 PACKAGE_MEMBER_UNCLASSIFIED. No ZIP bytes and no committed successful package.export
audit. Serialization/member failure after a provisional audit append still rolls back.
Invalid target case404. Policy writes use existing reviewed known/unknown outcome semantics.

## Revocation / identity boundary

Revocation that commits before export obtains its writer reservation is observed and denies.
Once export holds the reservation, concurrent policy update waits or times out503 with confirmed
not_committed; after it later commits, the next export denies. Existing full-lock A and proof
used to prevent audit lock inversion are preserved. No automatic write retry or claim that a
failed/unknown commit response proves no commit was added.

IMPORTANT: X-MCIS-Role remains a client-declared, unauthenticated local identity in this repo.
Server-side predicates now consistently use stored target-case policy for that declared role,
but this does not authenticate the subject or establish production access control. No claim
that a remote authenticated attacker can mutate SQLite/files is made. Cross-case tests use
real routes and explicitly synthetic stored-record anomalies where noted. DB/process trust
and recorded-hash (not source-authenticity) assumptions remain.

## Actual tests and one discovered omission

First implementation24 tests passed/4.89s. Independent review then found a real candidate
omission: scoped TrackPointRow.doc.caseId='OTHER-CASE' was exported. Its initial independent
run was10 passed/1 failed; this was a synthetic trusted-DB anomaly, not proof of remote
cross-case extraction. Added TrackPointRow to the same binding preflight, retained the
failing assertion, and verified ordinary point docs without caseId remain compatible.
No other product change was made after final independent review.

| Scope | Actual final result |
|---|---|
| Independent repair review:13 new independent+27 implementation+12 busy+6 authorization |58 passed/10.58s,0 skipped|
| Independent repair broad package/archive/digest/busy/contracts |172 passed,1 existing HFACS failure/43.70s|
| New combination original blocker alone |2 passed/1.33s (both now403)|
| New combination independent revalidation |52 passed/10.64s,0 skipped|
| New combination broad selected backend/acceptance |537 passed,5 existing failures,2 .NET skips/126.41s|

Counts overlap and must not be summed as unique coverage. Broad combined results are in
integrated-backend.txt. Five failures are same previously reproduced clean-main failures:
HFACS_CORE_UNAVAILABLE in test_report_versions_full_review_gisis_and_hfacs_coexist; old
interview_list_summary, redaction_by_role, crosscheck_requires_confirmation,
statement_add_and_review. Two skips require absent.NET. No assertions were removed/xfail'd.
The clean-main baseline evidence remains /workspace/mcis-main-integration-results/clean-main-baseline.txt.

New combination independent run includes the exact old two expected-denial regressions,
10 prior attachment/container integration tests,13 policy independent tests and27 implementation
tests. resolved-blocker.jsonl records actual loaded service path in the new tree and individual
and export statuses403; no mock denial. Ordinary allowed files and restored filename/hash,
no active restored receipt, current ZIP/DOCX gates, zero-audit cases, target-case policy,
foreign embedded binding rejection, malformed policy, ReadOnly/ReadWrite/Redacted/Deny,
real separate SQLite connection revocation ordering and rollback are covered.

Thread/DB concurrency uses real SQLite; controlled failures and test-only100ms busy timeouts
are explicitly simulations. Application busy timeout is unchanged. No model/intranet calls.
Frontend product files are unchanged from the previous build-tested combination; this
backend-only follow-up did not repeat frontend or real-browser acceptance. Earlier23+14
filename and88 intake checks/build evidence remains separate, not newly claimed here.

## Reproduce / deliverables

Standalone focused tests from independent repair service:
```
.venv/bin/python -m pytest -q tests/test_package_export_policy.py
.venv/bin/python -m pytest -q --import-mode=importlib ../tests_acceptance/package-export-policy/test_independent.py tests/test_package_export_policy.py tests/test_policy_write_busy.py tests/test_intake_authorization_transaction.py
```

New combination original blocker/independent checks from its service:
```
.venv/bin/python -m pytest -q --import-mode=importlib ../tests_acceptance/main-safe-attachment-integration/test_plain_policy_blocker.py ../tests_acceptance/main-safe-attachment-integration/test_independent.py ../tests_acceptance/package-export-policy/test_independent.py tests/test_package_export_policy.py
```

repair-product.patch / repair-with-tests.patch are incremental to13231d4, suitable for review
before applying to the combination; standalone and combined mcase hashes intentionally differ
because the latter retains the prior ZIP gate. main-integrated-candidate.patch is a full local
main-based artifact, not a pushed branch or approval to merge. Original historical blocking
reports should not be deleted; the new revalidation report supersedes their current verdict.

## Remaining limits

No true identity, trust/bootstrap, production credentials, streaming/memory bound, lock-latency
improvement, cancellation/fairness guarantee, source-authenticity guarantee or missing-digest
migration is provided. Whole-case raw export can intentionally deny more than old permissive
behavior, including Redacted categories and empty always-emitted members; no partial backup
is offered. Missing/malformed evidence digest still refuses, with no silent backfill. Files
remain mutable; digest-bound memory snapshot and source gates prevent changed-byte delivery.
Other endpoints, all policy semantics, actual browsers, .NET, CI and production environments
are not fully certified. Local repair closes the reported export-policy inconsistency only;
coordinator review is still required before any later integration decision.

## Final artifact verification

Generated main-integrated-candidate.patch (118 files: product, tests, contracts and retained
historical review logs) and main-integrated-product.patch (15 product files), with
integrated-file-manifest.json and frozen product hashes. The full patch passed
`git apply --check --cached --whitespace=nowarn` against the pristine main index at
3aba2bf03e393909c611489ae573a887087637ac. No patch was applied to main. Original repository
status remains clean and main unchanged. Full diff whitespace check reports preserved
pytest-log whitespace and inherited safe_files.py final blank line; frozen reviewed source
and historical failure logs were not rewritten for cosmetic cleanup. New local branches
remain uncommitted; no remote branch, PR, merge or deployment was created for this repair.

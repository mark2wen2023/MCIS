# Archive research versus PR104 — read-only dependency review

2026-11-16, developer evidence only. Remote main94d5e38c926fda232bb987b60fa9145e4bcf01a7 and PR104 b4df82306d9bab87b938b9e447e27a64b0464406 re-read. No product code changes, merge, deployment, PR description update/retry, restricted security/ECFC tests, real originals or model calls.

## Exact dependencies

Research tip2b4edd94f97a0c96c9fdcd11265fd8afd8be5436 has parent68c3e4ae3215a9b30be2b0c3c028bf830daf9c4b. Its ancestry includes d6dd764 (persisted operation/commit observation), f864976 (temporary SQLite continuation),6f7eb94 (offline v2 envelope) and earlier conflict/timeline candidates. Common ancestor with PR104 is94d5e38. Research side has36 commits,158 changed files (8328 additions/72 deletions);11 production module paths differ from common base. It also includes observation-editor/shared routing changes: not a minimal restoration patch.

Changed-path intersection with PR104 is only REQUESTS.md and ROADMAP.md. This is NOT proof of semantic integration, migration correctness, or acceptance of the entire research stack. No merge attempted. PR104's cases/package/package_intake runtime modules remain identical to main94d5e38. Research contains limited1.4 timeline support and additional unsupported-state detection that PR104 does not inherit; conflict ZIPv2 is still offline, not a product-supported format.

## Product boundary and actual missing links

- cases/service.py load_case/list_cases directly read CaseRow; no persistent readiness decision. Research wrappers have no product imports/callers.
- package/mcase.py export_case reads CaseRow and selects/validates existing supported formats, retaining409 refusal; it does not use the research readiness wrappers.
- package_intake/router.py has EXISTING IntakeReceipt and digest-based receipt lookup. It is incorrect to say there is no durable receipt. Receipt lookup resolves case identity separately from URL-based loading.
- commit_sync uses process WRITE_LOCK, SQLite BEGIN IMMEDIATE, staged import, source.mcase fsync, receipt flush, directory rename, then session-context commit. Exception handling can remove published target. This static ordering is not a joint filesystem/database commit protocol; this review did NOT inject a crash or uncertain commit and does NOT establish production data loss.
- Direct evidence routes and preview services bypass load_case; export, intake and digest receipts have their own case lookup. A load_case-only gate cannot establish universal pending-case isolation.
- Research PendingReadinessStore inserts waiting_publication in the restore transaction and holds every explicitly claimed/marked case. There is no ready promotion. Missing both tables is treated as legacy in the isolated contract; absent migration metadata cannot distinguish a genuine old database from loss of protocol state.
- Publication observer compares a synthetic file inventory and operation marker with database state, but explicitly cannot establish a synchronized filesystem snapshot or crash-safe publication. restore_ready remains false. Historical receipts stay non-authorizing; registry digests do not authenticate historical original bytes.

## Next necessary bounded work (not implemented here)

1. Define a durable database protocol/migration marker before wiring readiness. Genuine legacy databases must retain normal behavior; databases marked as protocol-enabled must not silently fall back to legacy when operation/readiness state is absent or inconsistent. Identify the exact migration owner and upgrade boundary first.
2. Map the claim, case, source-package digest, staged/final directory ownership, commit receipt and eventual ready state to one operation. Define each crash/unknown state without automatic deletion or retry. Directory publication and database confirmation must be independently observable, not inferred from one returned HTTP response.
3. Inventory and review all gates including direct services, list filtering, URL/body/digest-derived identities and transaction/reservation exclusions. Preserve existing authorization, ordinary metadata-only cases, old package behavior and unsupported409/422. No ready promotion or experimental import until these dependencies and independent end-to-end validation are complete.

Not safe to cherry-pick only readiness_gate into product: missing durable migration distinction and uncovered entry paths remain blockers. No new standalone simulation layer was added. Reuse existing research stores and receipts when implementing the bounded migration/gating contract, rather than inventing another receipt.

## Ordinary synthetic tests actually executed

Exact research checkout: /tmp/mcis-archive-readiness-review (detached2b4edd9). From its service/:
```
PYTHONPATH=.. /workspace/mcis/service/.venv/bin/pytest -q tests/test_conflict_readiness_gate.py
```
8 passed in5.23s. Covers legacy ordinary cases, held restored cases, same-transaction pending marker, rollback phases, process reopening, response lost AFTER actual commit, unknown schema and conservative state handling. The generic scoped-call callback is synthetic; not product endpoint/permission integration. Reopening in a subprocess is not a crash test, and post-commit response loss is not an uncertain SQLite commit.

Exact PR104 b4df823 checkout: /workspace/mcis-pr104-supported-archive. From service/:
```
./.venv/bin/pytest -q tests/test_archive_workflow_boundary.py::test_complex_seed_refuses_archive_without_partial_package_or_changes tests/test_case_metadata_w84.py::test_read_update_audit_original_and_roundtrip tests/test_vessel_entry_w91.py::test_create_reopen_export_and_audit
```
3 passed in1.42s. Existing supported synthetic workflows roundtrip; untouched complex demo rejects409/no partial ZIP/no temp DB or file-state changes. No unsupported case state removed. Did not run the separate default-role denial test or any restricted operation. Counts are different code trees, not an11-test integrated result.

No full research85-test rerun, combined-branch test, real crash, ambiguous commit, browser, production identity, real files, HFACS or model verification. Product recovery remains blocked; no claim of complete complex-case backup/restore. PR104 description update remains untouched after its earlier failure.

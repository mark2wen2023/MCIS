# Report + timeline 1.4 archive — independent acceptance

Tree `/workspace/mcis-report-timeline`, branch `feature/report-timeline-archive-v1`, baseline `f2eff95`. Read AGENTS/handoff, changed product/contract files and frozen manifest. Reviewer did not modify frozen implementation/tests, push, merge or deploy.

## Actual verification

```sh
PYTHONPATH=service service/.venv/bin/python -m pytest -q --import-mode=importlib \
 service/tests/test_report_timeline_archive.py \
 tests_acceptance/report-timeline-independent/test_boundaries.py
sha256sum -c logs/report-timeline-impl-hashes-frozen.txt
```

**33 passed in 17.56 seconds** (`results.txt`): 26 supplied cases plus seven independent cases. **All nine frozen file hashes match** (`hash-check.txt`). Tests use synthetic cases, real local API/SQLite/staged files; controlled failure/hold hooks are explicitly test instrumentation, not production fault evidence.

Supplied tests freshly rerun here cover three distinct stores preserving timeline row key/timestamps/doc, report and original source packages/audit prefixes; valid evidence-reference bytes; malformed versions/rows/mirror/source/time/budget; legacy import rejection; additional unsupported recommendation state; unauthorized requests; failure after timeline restore with transaction rollback; actual second-connection revoke waiting until reserved export finishes, then next export denied; legitimate submillisecond values preserved.

Independent additional cases cover:

* Capitalized extension namespace, boolean inner version, extra row field, working-v2/1.4 mixed version, and repeated nonexistent evidence references each reject with 422 before target rows/files appear. The last case combines duplicate and absent-reference invalidity; it is not standalone proof of duplicate detection for an otherwise valid reference. Code additionally checks duplicate reference identity explicitly.
* A newly populated unknown case-scoped SQLite table still causes export409 with snapshot counts unchanged.
* True/false confirmed flags, presumptive flag and original fractional time/doc survive import exactly and re-export remains1.4. Historical flag preservation is **not new confirmation**.

## Code / contract review

Version dispatch requires outer1.4.0, exact timeline path and working-record version1. Older 1.0–1.3 meanings remain separate. Track-history markers with1.4 and working-v2/1.4 mixtures are rejected; old import cannot receive a timeline extension without the already validated working capability. Unknown timeline namespace members fail the final allowed-member check. Timeline mirror is compared with the authoritative ordered row docs rather than restored independently.

The member schema rejects extra envelope/row fields and bounds 1–256 rows. Row validation checks keys/unique event IDs/case ownership, existing timeline schema and UTC row timestamps. Timeline-specific validation checks finite times, end>=start, case epoch consistency under the existing API's millisecond formatting, same-package vessel/evidence IDs and duplicate evidence IDs. Parser's existing evidence byte/hash validation and full-content/source permissions remain active. Contract now explicitly describes millisecond truncation while preserving original timeSec; both supplied precision cases pass. Frozen new/old contracts cross-reference the1.4 amendment, avoiding the earlier timeline refusal ambiguity.

Exporter only exempts timeline_events from closed-world state rejection within the working-record flow. It does not exempt conflicts, recommendations, consultations, COLREG, agents or arbitrary tables. Working-v2/track-history plus timeline remains unsupported. It materializes exact rows and mirror, validates, then parses the complete output before successful audit/export. Import's legacy mirror insert is skipped when the extension exists; restore adds the exact row timestamps/doc in the existing transaction. The provided failure injection demonstrates rollback at that stage, not crash atomicity across filesystem and SQLite.

Source1.4 archives are permitted as bounded historical bytes for re-export. Existing inspection does not execute nested archives, and imported actor/confirmation flags remain historical claims. Current policy is checked under the reserved transaction; tested late revoke cannot commit until that export completes. Subsequent requests observe denial. This is local SQLite policy consistency under role headers, not authentication or a distributed revocation guarantee.

## Compatibility and remaining limitations

**API-only:** inspected `web/src/packageIntake/model.ts` still accepts1.0–1.3 and rejects1.4. No browser/workbench support is delivered; do not advertise this as a completed normal UI backup/restore workflow. Current checked old service import rejects the new extension. This review does not certify every historical external/Unity reader.

Imported confirmed/presumptive fields retain existing listing/filter behavior; no new historical-status UI indicator exists. Exact retention prevents accidental rewriting but does not establish truth, identity or approval. No numerical-core, production load, real evidence or browser validation in this independent run. Long writer reservations, in-memory archive assembly, role-header trust and inherited filesystem/DB crash/reconciliation limitations remain.

Coordinator's expanded regression logs (read, **not rerun here**) show 135 passed/1 HFACS failure and a track selection with its own HFACS failure; separate parent logs reproduce the two named failing nodes. Those outcomes cannot be called all-green or attributed to this33-case independent run. This review neither fixes nor independently re-diagnoses them.

## Disposition

**Accept the frozen bounded API candidate within the tested report/working-v1 + timeline scope.** No new safety/version/rollback blocker found in this review. This is a versioned supported subset, not a six-table allowlist bypass or universal mixed-case backup. Track combinations/unknown states remain rejected, UI integration remains outstanding, and no merge/deployment authorization is implied.

Coordinator final frozen combined regression subsequently completed: **171 passed, 2 failed in 60.11 seconds**, read from `tests_acceptance/report-timeline/final-regression.txt`. Failing nodes are the working-record and track-history HFACS coexistence cases with parent reproduction logs as above. This supersedes the earlier coordinator selection counts for combined coverage; it is not another independent execution and must not be summed with33. Independent acceptance result remains33 passed; combined regression remains non-green with the two documented baseline failures.

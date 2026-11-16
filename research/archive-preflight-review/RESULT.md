# Bounded archive preflight convergence

## Exact dependency and scope
Base: `658f877b2f88e17a2cf19601811184df11cc98a9` (registered WAV candidate).
Remote main observed: `94d5e38c926fda232bb987b60fa9145e4bcf01a7`.
Reviewed old patch: `88339848934e4c35523618587ad47b32c96869b4`, parent `a7ce17bce4a74cf998fb3241efad12889779905f`.
Old patch is not an ancestor. It relies on unmerged timeline 1.4/origin and prior consultation work. No cherry-pick of that stack: only its seven-model existence loop is adapted (10 added runtime lines). The current parser remains 1.0–1.3; timeline remains rejected, unlike the old 1.4 candidate.

Current main, image candidate 91962113 and audio base share identical archive exporter, working-record builder and parser blobs. Existing closed-world table checking already rejects unsupported data when reached. The defect is bypass of that check by standalone states with no recognized history. COLREG `inputs` and simulation commands are not serialized by the legacy file builder at all; other listed nonempty sections are refused by the legacy parser. These are code-path findings, not production data-loss observations.

## Developer ordinary tests
Before runtime patch, corrected new test subset: **8 failed, 2 passed**. Eight standalone synthetic storage states exported HTTP200 instead of expected409. Two empty-case/other-case ordinary roundtrips passed. An initial test-authoring run used an incorrect manifest field (`schemaVersion` rather than `packageVersion`); fixed before recording that baseline. No product behavior was changed to accommodate it.

Final command (repo root):
```sh
PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q \
 service/tests/test_archive_preflight_audio_base.py \
 service/tests/test_working_record_archive.py::test_three_store_roundtrip_and_inactive_receipts \
 service/tests/test_track_history.py::test_three_stores_original_bytes_and_inactive_receipts \
 service/tests/test_audio_review_candidate.py::test_synthetic_roundtrip_unknown_history_download_and_archive_refusal \
 --tb=short
```
Exact selected nodeids are in `nodeids.txt`. Baseline outcome summary and final outcome below refer only to these explicitly described selections, not any previous 96/109 or full-suite count.

Coverage: eight standalone storage fixtures and the same eight with an extra timeline event; 409/no ZIP/SQL rows unchanged/non-database file bytes unchanged. Four additional API-created ordinary states (recommendation, conflict, agent draft, simulation command) retain all SQL rows after refusal. Fixtures are synthetic and do not represent COLREG inference, Unity execution or LLM output. Two successful empty-case roundtrips (one with another case's unsupported row) cover existing 1.0 import and subsequent working-record re-export. Existing selected three-store tests cover 1.2 report/interview/source/history and 1.3 track original bytes/inactive receipts. Existing audio review roundtrip still rejects archive export; source/review content remains available through its existing candidate flow.

## Limits
Not independent acceptance, not whole-repository regression. No 1.1 real HFACS test, 1.4 support, browser, production authentication, real-case media, crash or uncertain-commit verification. Image branch is not merged into this audio candidate. No media archive format or restoration enabled. No permissions, table allowlist, parser, recovery transaction or file-publication changes. No previously restricted security/ECFC/browser suite rerun, no vulnerability reproduction, no PR body update, push, merge or deployment. Unknown/future tables and audit-only standalone states are not exhaustively validated. Existing WAL behavior is unchanged; SQLite investigation is separate from this ordinary business fix.

Final developer outcome: **25 passed in 7.41s**, 0 failed, 0 skipped. Nodeids use pytest service-root-relative paths. No independent result claimed.

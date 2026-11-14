# Archive candidate migration onto main73fc800

## Exact base and scope

Remote main was fetched and checked again after tests: **73fc8002868d9c6894b5fce6d03f7db690291bf6**. Candidate being migrated: **6203a0cbaf3dad7a95e3a5894ef2ae6660575ad3**, whose parent is4a6e729. New isolated branch: `research/archive-main-73fc800`, based directly on73fc800. No remote push, PR, merge or deployment in this task.

Main's new #78 adds only offline expert-receipt foundation, scope/tests and process records:20 paths, including REQUESTS/ROADMAP. It does not alter production service/web code. Its module remains for trusted private local single-writer consistency checks, not authentication, model execution, hostile uploads or a case-evidence filesystem boundary. The archive service does not import/wire it.

## Differences and conflict resolution

`git merge-tree --write-tree 73fc800 6203a0c` reports only append conflicts in REQUESTS.md and ROADMAP.md; full output is in migration.json. No production source/schema/UI conflicts. A new worktree on73fc800 received the exact candidate delta relative to4a6e729, excluding those two files. Their resolution preserves full latest-main text followed by the exact candidate append suffix. No git merge command/merge commit, main ref modification or protection bypass was used.

All63 nonconflicting candidate paths match6203a0c byte-for-byte; all18 new-main non-document paths match73fc800 byte-for-byte. Two document histories are retained, including the receipt-module warnings. Independent confirmation is in independent-hashes.json/independent.md. No report+recommendation research is folded into the working archive. There is no97-commit stack.

A new migration hash manifest is logs/archive-main-73-hashes.txt. Inherited hash manifests/reports describe their original earlier snapshots; their old REQUESTS/ROADMAP hashes are historical, not assertions that those files stayed unchanged after #78.

## Actual validation

```sh
PYTHONPATH=.:service:tests_acceptance/EXACT_SAMPLE service/.venv/bin/python -m pytest -q --import-mode=importlib \
 service/tests/test_report_timeline_archive.py \
 tests_acceptance/report-timeline-independent/test_boundaries.py \
 service/tests/test_working_record_archive.py \
 service/tests/test_package_intake_parser.py service/tests/test_package_intake_router.py \
 service/tests/test_archive_export_safety.py service/tests/test_track_history.py \
 service/tests/test_environment_w92.py \
 tests_acceptance/EXACT_SAMPLE/test_exact_sample.py tests_acceptance/EXACT_SAMPLE/test_independent.py \
 tests_acceptance/aeb-main-integration/test_mixed_history.py \
 tests_acceptance/EXPERTRECEIPT/test_receipt.py tests_acceptance/EXPERTRECEIPT/test_independent.py
```

**298 passed,2 failed /83.59s** (backend.txt). The failing nodes are the same working-record and track-history actual HFACS-core workflows. A fresh unmodified detached73fc800 control worktree ran those exact nodes: **2 failed /1.97s**, HFACS_CORE_UNAVAILABLE (main-control.txt). No mock core, installation or skip substituted for these failures; this does not imply a green full suite.

Independent reviewer ran26 timeline/report cases +7 independent archive boundaries +35 offline receipt cases: **68 passed /18.12s**. It checked the full file-preservation/conflict resolution and absence of production coupling to expert receipts. This68 overlaps the coordinator suite and is not additive unique coverage.

Actual synthetic local ASGI flow in the migrated tree:1.4 preview/commit/receipt200 with exact timeline rows; Investigator403; wrong track-version422 with no destination case. The actual service responses pass frontend parsing/receipt binding and React SSR (api.txt/ui-responses.txt). `npm run build` passed with the known large-chunk warning (build.txt). These are not real browser interactions or production identity validation. No UI/service code was newly edited during migration.

## Release gate remains closed

Real browser validation is still uncompleted. The preceding sandbox-enabled Chromium attempt aborted before page creation due to its SUID helper ownership; no new sandbox bypass, plugin installation or helper change was attempted here. Historical concrete browser evidence is retained under tests_acceptance/aeb-main-integration/browser-sandbox.txt. The current migration reuses byte-identical UI, but that does not turn earlier ASGI/SSR evidence into browser acceptance. File selection/confirmation/receipt/navigation/unknown-write recovery need actual sandbox-capable browser verification.

The two HFACS-core baseline failures also remain unresolved; optional HFACS workflows must be exercised with the actual core before claiming them validated. GitHub CI/required approvals/protection and production deployment readiness are not certified by local tests.

Bounded1.4 scope remains working records + timeline events, retaining original records/source/audit history. Track+timeline, safety recommendations, consultation, conflicts, COLREG, agent/unknown states continue to refuse. Header identities, long write locks, memory bounds and filesystem/database crash or unknown-commit limitations are unchanged. **This is a saved migration candidate, not permission to merge or deploy.**

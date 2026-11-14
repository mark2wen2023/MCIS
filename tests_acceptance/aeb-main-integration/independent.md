# Independent current-main synthetic integration review

Scope: local uncommitted combination in `/workspace/mcis-aeb-main-integration`, HEAD `4a6e729`, with the aeb8cf1 feature delta relative to f2eff95 applied. This is not a remote merge or release. The previous f2eff95 → aeb8cf1 no-conflict result does not apply to this later main; the previous independent report has an explicit main-advanced addendum.

## Source preservation checks

Independently compared every service/web/contracts file in `git diff --name-only f2eff95 aeb8cf1`: all **13 files** have identical SHA-256 hashes to their aeb8cf1 contents. See `independent-hashes.json`. `service/mcis_service/cases/service.py` and `service/tests/test_environment_w92.py` are byte-identical to HEAD4a6e729: #75's four-line exact-sample metadata preservation and #76's isolated environment fixture/denial regression remain present.

REQUESTS.md and ROADMAP.md were independently checked to equal the complete current-main file followed by exactly the append suffix from f2eff95 → aeb8cf1. Both sets of records survive resolution. Therefore this is a verified local documentation conflict resolution, not a claim that the latest main merge is conflict-free. No product files or implementation tests were edited by this reviewer.

## Fresh independent execution

```sh
PYTHONPATH=service:tests_acceptance/EXACT_SAMPLE service/.venv/bin/python -m pytest -q --import-mode=importlib service/tests/test_report_timeline_archive.py tests_acceptance/report-timeline-independent/test_boundaries.py service/tests/test_environment_w92.py tests_acceptance/EXACT_SAMPLE/test_independent.py
```

**107 passed in 39.91s**, recorded in `independent-tests-corrected.txt`: 26 feature cases + 7 independent archive boundary cases + 70 environment cases + 4 independent exact-sample cases. This checks the explicit current-main synthetic combination, including retained #75/#76 behavior. It is not a full-service green result.

The first invocation used only PYTHONPATH=service and failed collection because EXACT_SAMPLE/test_independent.py imports its sibling test_exact_sample by bare name. The original `independent-tests.txt` is retained (one collection error). Only the command environment was corrected; no assertions or implementation were changed.

## Other evidence and remaining blockers

Inspected the coordinator's fresh `api.txt` and `ui-responses.txt`: actual local ASGI preview/commit/lookup 200 and timeline equality, Investigator403, track-version mismatch422 with zero cases, then frontend parsing/SSR against those responses. These were not independently rerun by this reviewer. `build.txt` records a successful 931ms build with the large-chunk warning. The wider `backend.txt` was still running at inspection, so no final result is inferred here.

Sandboxed browser interaction remains blocked by the previously documented Chromium SUID helper ownership problem. There was no new browser attempt or sandbox bypass in this review. API/SSR/build evidence is not a browser acceptance result. The prior two HFACS-dependent failures remain known unresolved baseline blockers pending the coordinator's final expanded result; this focused107 does not exercise them or establish their resolution.

Verdict: this exact synthetic tree passes the requested focused combination and source-preservation checks. Full integration release remains blocked/unverified for browser interaction and HFACS-dependent workflows. The supported bounded1.4 profile, rejected unknown/mixed state families, synthetic role-header identity, existing resource/locking limits and filesystem/database failure boundaries are unchanged. No PR, commit, push, merge or deployment was performed by this reviewer.

# Independent archive migration review on main73fc800

Reviewed local branch research/archive-main-73fc800, HEAD73fc800, with the6203a0c delta relative to4a6e729 applied but not committed/merged remotely. This report concerns this synthetic combination; earlier f2eff95 or4a6e729 results are not substituted for its execution.

## Exact preservation

`independent-hashes.json` records SHA-256 equality for all **63 non-document-conflict candidate paths** against6203a0c and all **18 non-document-conflict new-main paths** against73fc800. The main delta has20 total paths, including REQUESTS.md and ROADMAP.md. Each documentation file was independently asserted equal to complete main73fc800 content plus the candidate's exact suffix relative to4a6e729. Both histories survive; this is resolved append conflict evidence, not a conflict-free merge claim. AGENTS.md and the handoff were read. No implementation was modified by this reviewer.

## Independent fresh tests

From repository root:

```sh
PYTHONPATH=.:service:tests_acceptance/EXACT_SAMPLE service/.venv/bin/python -m pytest -q --import-mode=importlib service/tests/test_report_timeline_archive.py tests_acceptance/report-timeline-independent/test_boundaries.py tests_acceptance/EXPERTRECEIPT/test_receipt.py tests_acceptance/EXPERTRECEIPT/test_independent.py
```

**68 passed in18.12s** (`independent-tests.txt`):26 archive feature cases,7 archive independent boundaries, and35 receipt cases across the two specified modules. This is a focused combination result, not full-service or browser acceptance. The coordinator is running the wider combination separately; its outcome is not inferred here.

## Receipt integration and trust boundaries

Read research/expert_group/receipt.py and RECEIPT_SCOPE.md, and searched service/mcis_service,web/src,contracts for expert_group,verify_export and research receipt references: none found. The current product service does not wire this research receipt module. This static search and the exact source preservation do not prove the absence of every possible external/dynamic integration.

The module uses local standard-library filesystem/JSON/hash operations; it provides local consistency only. Its successful verifier result always sets authenticityVerified=False and factActivated=False; failed/partial/cancelled/unknown run status is not converted into successful execution. It is not an authorization gate, signature, provider/model-call proof, SSO, causal truth or consensus. O_EXCL writes use0600, but that does not make arbitrary directories trusted. Final directory/leaf symlinks are refused; ancestor symlinks, separate-read races and trusted local single-writer assumptions remain expressly documented. Receipt row schemaVersion True can compare equal to1; transportMocked is not type-validated during verification; token restrictions do not detect secrets. Incomplete writes can leave files. These are acknowledged scope boundaries, not fixes delivered by the archive migration. The scope does not overclaim production expert-feature integration or hostile-import safety.

## Verdict and unresolved acceptance

The exact migration preserves both reviewed deltas and passes the requested68 focused cases. No new integration failure was observed in that scope. It does not resolve the known HFACS-dependent baseline failures, browser-interaction gap, synthetic role-header identity, or existing memory/lock/filesystem-database limits. Browser sandbox failure remains blocking for full interactive acceptance; this reviewer attempted no browser workaround, plugin installation or helper/permission change. No product modification, PR, push, merge or deployment was performed. Full release approval is not established by this focused review.

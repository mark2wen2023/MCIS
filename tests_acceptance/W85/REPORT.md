# W8.5 independent acceptance

## Result
- Independent API suite: **17 passed**, using isolated temporary SQLite/blob storage.
- Real Chromium headless shell + real FastAPI + real Vite proxy: **passed** preview → explicit confirmation → commit → GET receipt → case link. Original archive remained byte-identical; no browser page errors.
- Implementation SHA-256 recorded in `verified-impl-sha256.txt` and rechecked after tests.
- No implementation changed by this reviewer; no publication/deployment/W11 work.

## Defects found and fixed by implementation owner
1. Audit line splitting differed: parser split only LF, old importer used `splitlines()`. Raw U+2028 inside JSON content previewed successfully but commit rejected the chain. Original run: **10 passed, 2 failed**. Both failures had preview HTTP 200 followed by commit HTTP 422 `CHAIN_BROKEN` / `bad json`, once with LF and once with CRLF. Original assertions remain in `test_accepted_audit_lines_import_exactly`.
2. BOM acceptance differed: parser accepted JSONL UTF-8 BOM while importer rejected it. BOM-only original run: **1 failed, 12 deselected**, with preview HTTP 200 followed by commit HTTP 422 `CHAIN_BROKEN` / `bad json`. Original assertion remains in `test_accepted_bom_audit_matches_import`.

Owner chose documented restrictive profile: only LF chains, no raw alternate newline characters; JSON BOM rejected. Same independent red tests now pass by explicit preview rejection; normal LF audit positive test proves original line retained with exactly one appended local import event.

## Coverage
No-write preview; original archive SHA and bytes; idempotent same-package receipt; only-new-case semantics; same-case/different-package concurrency; investigator-only endpoints; policy changed after import rechecked on receipt; unknown members and nonempty unsupported business content rejected; final DB commit failure rolls SQL/files back while unrelated sentinel remains; existing symlink not followed; original archive corruption blocks recovery/reimport; LF provenance chain preserved.

## Test-harness corrections / environment limitations
- Initial policy test used nonexistent `grants` field, not actual matrix. Corrected fixture to deny `matrix.Investigator.evidence_meta`; the exploratory result was **15 passed, 1 failed** before correcting that fixture. This was a test mistake, not a product defect.
- System Chromium could not create its singleton socket under this execution environment. Raw diagnostic logs are retained locally, not included in this PR. Existing headless-shell executable worked with the same real-API acceptance script.
- One Starlette/httpx deprecation warning; does not affect assertions.
- This acceptance does not establish production authentication, multi-process safety, filesystem/SQL crash atomicity, all legacy package compatibility, or arbitrary multimodal interpretation. UI unknown-outcome/lifecycle doubles are implementation-owner self-tests, not counted among this reviewer's 17 API tests.

## Publication scope
Raw execution logs, temporary files and Python cache are excluded. The three original product regression assertions remain unchanged and pass after the documented restrictive-input fix. Local raw logs are retained for audit; the concise outcomes above are the published record.

The subsequent OpenAPI path-prefix correction was outside this report’s frozen implementation list and did not change its recorded hashes.

## Reproduce
From repository root:
```
cd service
PYTHONPATH=. .venv/bin/pytest -q ../tests_acceptance/W85/test_intake_independent.py
cd ..
MCIS_BROWSER_BIN=<existing-headless-shell> python tests_acceptance/W85/browser_real.py
```

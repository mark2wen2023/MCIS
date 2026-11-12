# W4.2 independent acceptance

Status: freeze2 independently run on baseline 096e3d2. In-process API 71/71; real HTTP 1 combined scenario; real Chromium 6 groups, all PASS. Freeze1 found W42-A01 (= D01), original failure retained; freeze2 fixes it. See DEFECTS/W4.2.md for evidence and limits.
No implementation tests reused. All fixtures are synthetic; no production data, execution of file content, OCR or ASR. Only 127.0.0.1 listeners. Service uses service/.venv; browser uses existing Playwright and MCIS_BROWSER_BIN.

| Group | Independent assertions |
|---|---|
| Protocol | binary/empty, strict base64/JSON/UTF8, duplicates/unknown/nonfinite/depth, 8MiB file and 12MiB body, exact metadata originals, date UTC whole seconds and years 1000–9999 |
| Preview/commit | no DB/file writes on preview, explicit confirmation/digest binding, distinct extraction/registration UTC, original immutable bytes, no overwrite/symlink |
| Persistence failures | actual Session commit failure after flush, write failure, cleanup failure reported, rollback of evidence/register/audit; no crash-ACID claim |
| Idempotency | concurrent same request one register; different requests same bytes distinct evidence; read-only receipt recovery after lost reply |
| Authorization | roles, evidence_meta read/write matrix, testimony plus Restricted fieldRules; all five endpoint families |
| Integrity | changed/deleted original; altered metadata/register/path; unsupported Change; original note survives legitimate note edit |
| Package | export/import fresh DB, exact original plus all custody lines preserved, receipt/download works |
| Browser | local selection no upload, preview/confirm invalidation, double click, XSS literal text, lost write response/read-only recover, delayed case/role/navigation/selection/session response isolation, in-flight write completes after leave, reopen/download byte equality, 1440/1920 keyboard |
| Regression boundary | W10/W8.4 combination and full service/Web regression are coordinated separately, not included in these independent W4.2 counts |

Run API after freeze: `PYTHONPATH=service service/.venv/bin/pytest -q -p no:cacheprovider tests_acceptance/W42/test_api.py`.

Real HTTP/browser: `MCIS_BROWSER_BIN=/path/to/existing/chrome-headless-shell W42_RUN_LABEL=unique-label python tests_acceptance/W42/browser_run.py` (global existing Playwright, service/.venv for both servers; ports18842/18843/15842). Use a new label to preserve old logs.

Published evidence: `logs/w42-independent-freeze1-results.json` (1 HTTP PASS, 3 browser PASS, 1 browser FAIL), `logs/w42-independent-freeze2-results.json` (1 HTTP PASS, 6 browser PASS), Freeze2 PASS log and pre/post hash checks, and `logs/w42-independent-review.md`. Original API warning logs, red stack/server logs and screenshots are local-only retained evidence, not repository attachments. Freeze1 hashes are `logs/w42-impl-hashes-frozen-v1.txt`; current `logs/w42-impl-hashes-frozen.txt` is Freeze2.

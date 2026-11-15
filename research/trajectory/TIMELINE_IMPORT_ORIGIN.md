# Latest-import timeline origin candidate

Independent branch candidate/timeline-import-origin, exact parent
 e68bacc448311528a574f11ef1800213a384fd94 ->
 2cb43812eaa9e43e938748085cb5fed39c22b331 ->
 94d5e38c926fda232bb987b60fa9145e4bcf01a7.
Remote main freshly checked this turn remains94d5e38. Requires the unmerged bounded
backend and frontend1.4 candidates; not a standalone main patch. No remote changes.

## Implemented

Validated intake records a case/event/package/exact-row digest in a new derived
SQLite table in the same transaction as case, audit and receipt. It never accepts
client origin metadata. GET timeline keeps its existing permission check and adds
only origins for returned events. Match is against current stored row AND returned
doc, including original row timestamps. Missing record, receipt mismatch, changed
row or another case does not receive a restored label.

The table is a cache, with no additional historical business facts. Export checks
it can be reproduced from the retained source bytes before omitting it; it is not
merely exempted from unsupported-state protection. Presence also forces the existing
history-aware export path. Subsequent import derives a new latest-package binding.
Old package bytes, receipts, audit lines and lineage stay in the existing archive;
first-generation sources remain in a third-store export. No new archive member or
format relaxation. Old stores without an index remain unknown; no guessed backfill.

Always-visible UI lists each event: proven members are restored historical claims,
not this import's approval. Other records say origin unavailable, without calling
them local/new/approved. Existing confirmed/presumptive values are preserved.
There is no current-review proof endpoint, so the UI explicitly says so.

## Developer validation

Synthetic HTTP workflows only, temporary directories/SQLite; no private case data,
actual models, prohibited historical-integrity probes or ECFC operations.

Repository root command:
```
service/.venv/bin/pytest -q service/tests/test_timeline_import_origin.py service/tests/test_bounded_timeline_archive_increment.py service/tests/test_contracts.py service/tests/test_environment_w92.py service/tests/test_working_record_archive.py::test_three_store_roundtrip_and_inactive_receipts
```
Final result: **87 passed in26.52s**, no failures/skips in this selected set. New tests include restored/new mixture, filtering,
second-generation bindings and preserved previous raw packages, old database without
index (prior importer simulated), old1.0 package, same eventID in another case,
Public403/no writes, and injected ordinary index failure with full rollback.
One pure unit test uses dependency stubs to test new derived-cache rejection of
missing/mismatched source and unmatched rows; it is not an actual model evaluation.

From web:
```
./node_modules/.bin/esbuild tests/timeline-origin.test.tsx --bundle --platform=node --format=cjs --outfile=/tmp/mcis-timeline-origin-test.cjs --jsx=automatic --log-level=warning
node /tmp/mcis-timeline-origin-test.cjs
./node_modules/.bin/esbuild tests/bounded-timeline-intake.test.tsx --bundle --platform=node --format=cjs --outfile=/tmp/mcis-bounded-origin-test.cjs --jsx=automatic --log-level=warning
node /tmp/mcis-bounded-origin-test.cjs
npm run build
```
9 new synthetic SSR assertions,68 existing bounded-intake assertions passed. Final
TypeScript/Vite build passed, existing >1500kB bundle warning. Initial build found a
missing optional frontend caseId type; fixed in the new component boundary.

Browser plugin unavailable. Checking existing service Python with
`from playwright.sync_api import sync_playwright` failed ModuleNotFoundError.
No browser installed, launched, sandbox disabled or screenshots collected. Page
identity, interaction, mobile layout, console health and browser rendering NOT tested.
Do not confuse SSR/build with independent browser acceptance.

## Limits

Most-recent-import association only, not a full lineage viewer, first creator proof
or signed source authenticity. No cryptographic defense against arbitrary database
administrator modification. Source-file presence is checked at export, not during
ordinary listing. Original archive read permissions unchanged. No new human-review
operation, identity authentication, crash-atomicity or concurrent performance proof.
Extra bounded original ZIP decoding at export has not been load tested; prior memory
and long-lock limitations remain. Old readers may display no badge. Old stores with
missing indices remain unclassified until a real new import; never guessed.

Complex cases and timeline+track-history remain refused. Original190 regressions
and prior two frontend wording failures are not rerun or claimed fixed. HFACS/core,
LLM, full suite and independent acceptance not executed. No push/merge/deployment.

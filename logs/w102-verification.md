# W10.2 strict UTC CSV first-input verification

## Delivered scope

This is the original W10's first persisted-input slice, not an arbitrary AIS importer or all of W10. A registered vessel with no existing points can accept the fixed **MCIS-UTC CSV v1** profile: local file selection, real read-only server preview, explicit human confirmation, first save, verified receipt recovery, and restricted original CSV / derived report download. The original bytes, source/time declarations, row diagnostics, evidence registration, custody and audit are retained. The normal W10.1 saved-point reader consumes the saved points. Existing `.mcase` transfer includes the indexed original/report.

The professional and engineering basis, precise fields, units, statuses and limits are in `contracts/W10.2-track-input.md`. A reported 102.2 kn is **not** inferred to be AIS raw-code saturation. Unknown/unavailable required values and declared lower bounds block saving; the original bytes preserve those declarations. Complete explicit UTC dates are mandatory. No guessed date/timezone, silently dropped row, automatic sorting, cleaning, interpolation, NMEA/message-27 decode, generic column mapping, replacement or append is implemented.

## Independent result before serial integration

- Independent session: **43/43 scenarios**, comprising 35 actual HTTP/storage and 8 actual Chromium scenarios on synthetic fixtures. It did not reuse implementation self-tests.
- D01 was found independently: a historical receipt did not prove current points remained complete after injected storage corruption. The original red assertion remains. Recovery/list/download/idempotent retry now revalidate bound source/configuration/current epoch and every stored point, fail closed with 409, and do not repair data. Independent v2 closes D01.
- Both ends of the final independent run match all 12 frozen implementation hashes. The original v1 freeze, red results and defect history are retained.
- Atomicity exercised: second-file failure, actual database-commit failure, cleanup failure, identical/different concurrent requests in one service process. These tests do **not** establish crash/ power-loss atomicity across SQLite and files or multiworker concurrency.
- Source BOM/CRLF bytes, SHA, raw/report downloads, `.mcase` transfer to a fresh database, all saved point documents and audit-line prefix preservation are checked. No independent cryptographic audit-chain recomputation is claimed.
- Desktop 1440/1920, metadata/file invalidation, human confirmation, duplicate click, response loss followed by read-only recovery, navigation/role late-response suppression, and an already-issued write completing after navigation are exercised.
- A 10,000-row browser preview retained 100 samples and 20 DOM rows per page; observed preview latency 0.301 s in one run is not a general benchmark.

See `logs/w102-independent-final-review.md`, `DEFECTS/W10.2.md` and `tests_acceptance/W102/README.md`.

## Self/regression evidence before W8.4 integration

- All `service/tests`: **776 passed**, with current pinned C# source-built core and complete exact test-support sources. Earlier runs with incomplete materialization / unwritable default SDK home were not passing evidence; fixed source/support files, executable modes and writable SDK home were used for this run.
- Frontend: **1,129 assertions** across all existing runners and standalone context/lobby/vessel tests; TypeScript/build passed. Source lint exit 0 retains existing warnings; the dedicated new module has no warnings. Existing bundle-size warning remains.
- W10.2 implementation browser: **13 actual Chromium checks** against actual service/Vite, not simulated API success. Independent 43 remains separate evidence.

## Reproduction and limits

Use project service `.venv`, existing Node dependencies, an installed .NET SDK/core, and an already-installed Chromium selected through `MCIS_BROWSER_BIN`. Both browser runners start backend/Vite/browser in one process tree, bind only `127.0.0.1`, use fresh temporary synthetic databases and terminate services. They install no software. See the independent runner README and `web/tests/track-input-w102.browser.py`.

Still not covered/delivered: arbitrary AIS/platform CSV, encoded-message decoding, saturation inference without encoded provenance, production authentication, multiworker concurrency, process-crash ACID, full mobile/accessibility audit, every exact budget boundary, all 10,000 saved points' reader-page interactions, Unity, deployment. Human source/time declarations and hashes are not proof of evidence authenticity or complete chain of custody. Existing package import limitations remain; this slice does not expose package import in the UI.

## Serial integration

Awaiting W8.4's exact merged main. No W10.2 remote branch/PR or merge existed at this pre-integration checkpoint. Final combined-tree verification is recorded below when complete; this checkpoint alone is not a release claim.

### Final combined-tree result

- Integrated exact W8.4 main `7c1208daef26fd263b87edd9d06bab3d6b267725`, tree `324d78e4cbf0928c98043ab30c2bf3bd09861147`. All 35 changed blobs were verified before applying only the registered W10 additions. W8.4 case context, layout, lobby, metadata behavior and routes are retained.
- Full `service/tests`: **823 passed in 256.60 s**, no failures or skips, on the final combined implementation.
- Full frontend runners and standalone context/lobby/vessel tests: **1,225 assertions passed**, TypeScript/build passed; source lint exit 0 with 12 existing warnings. Existing bundle-size warning remains.
- W10 independent final integration: **45/45**, 37 actual HTTP/storage + 8 actual Chromium, original 43 retained plus two description-edit cross-package scenarios. All 12 freeze hashes match at both ends. Description-only W8.4 edits preserve W10 epoch/digest/confirmation and saved source/report/points/receipt.
- W8.4 affected regression: **42 independent behavior tests + 4 contract tests passed**. Its original whole-file freeze test predictably fails on registered shared `main.py`/OpenAPI additions; the original assertion and freeze are untouched. It is **not** reported as 47 green. A selected rerun records 46 passed / 1 deselected. Separate independent preservation checks are **20/20**: 6 nonshared backend and 10 UI hashes, exact original full-file hashes after stripping only W10 additions, and metadata GET/PATCH in contract and runtime.
- W8.4 actual-backend browser: **39 assertions passed**, plus all three retained legacy-empty/whitespace-title repair checks. W10 implementation actual-backend browser: **13 checks passed**.
- Main/OpenAPI are shared-entry additions; no W8.4 business implementation or old freeze changed. W10.1 TrackPage's intentional input-panel integration is recorded in REQUESTS; original W10.1 artifacts remain unchanged.

Published acceptance artifacts are the explicit test sources, defect history, frozen hashes, concise reviews, red-result JSON and final result/log evidence. Environment bootstrap failures, local screenshots, databases, debug/server logs, dependencies and compiled artifacts are not published. Nothing is deployed.

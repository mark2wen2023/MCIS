# W8.3 independent acceptance — 2026-11-12

## Decision
**Desktop-limited W8.3 slice accepted after D01 repair. Not full W8, mobile or deployment acceptance.**

- Actual HTTP: **14/14**.
- Actual Chromium: **32 passed + 1 known shared-shell mobile defect**, 0 uncaught JS exceptions. Real service for export/download/precheck/hash mutations; only specified failure/race cases use mocked responses.
- Independent component lifecycle harness: **28/28**; mocked hooks/fetch/DOM, not counted as browser tests.
- Final implementation freeze: **9/9 exact SHA-256 matches**.
- Final integrated main baseline: `e8db196982d633579de38bca65ed2cd36d96becc` (includes W9). Runtime service **78 Python source files exactly match** this commit; see service-baseline-differences.json. No production service changes by this slice/test agent.

## Findings and repair
D01 was independently reproduced on the original frozen implementation: navigation URL changed before React unmount, so a delayed report appeared after rapid Back. It was not dismissed as a test timing issue. Implementation repaired navigation-intent/history cancellation; the original rapid Back test is retained and now passes, along with normal Back/Forward and delayed export navigation. See DEFECTS/W8.3.md, fast-back-pre-fix.txt and final browser-results.json.

K01 remains: 390px viewport has document scrollWidth 732px both with and without W8.3 elements. The old shared shell/topbar/sidebar is the source. 1440×900 and 1920×1080 pass horizontal-overflow checks and screenshot inspection. No claim of mobile readiness.

## Verified behavior
Real exported .mcase downloads as ZIP and is successfully prechecked by the actual service. Selection alone does not upload. Missing and changed files produce failure; extras remain a separate caution. Empty/non-mcase file rejected in UI. Real bad ZIP returns 422. Mocked 403/500/malformed reports never produce success. Same-render and browser double clicks issue one request. New selection, cancellation, close/reopen, identity change, rapid navigation, normal Back/Forward suppress stale results. Public cannot see complete-package tools. Encoded case IDs and download MIME/empty/error boundaries covered by the independent harness. Actual export role restrictions covered over HTTP. W9 ships navigation→Back works after integration.

## Environment and reproducibility
CUA cloud browser first failed to reach exec-local loopback servers (`ERR_CONNECTION_REFUSED`). Under engineering-test authorization, existing Playwright + installed official Chrome headless shell were used in the same exec process tree as Vite/uvicorn. No software installed, no external server or deployment. Servers bind only 127.0.0.1 ports 15883/18883; data is new temporary SQLite/blob storage, seeded only with fictional Lily/Mary. No import endpoint called, and case list remains unchanged.

The service was materialized into a temporary runtime copy to isolate existing work; all 78 Python files were checked against integrated main (zero differences). Default runner uses normal repository service/.venv and service source. Overrides used here: MCIS_W83_SERVICE_ROOT=the acceptance runtime copy, MCIS_W83_PYTHON=existing service venv, MCIS_BROWSER_BIN=existing Chrome headless shell, MCIS_W83_ARTIFACT_DIR=local acceptance artifact directory. See README for portable command/overrides.

Initial harness issues were corrected without changing production code: Playwright callback received a Request as the second argument, and one screenshot raced a source hot reload during W9 materialization. Final run uses frozen source and no such failures. These are not application pass/fail counts.

## Evidence and publication boundary
Commit only source tests, README, this review, DEFECTS, final/pre-fix text/JSON results and service-baseline comparison. Do not commit runtime source copy, generated CJS, fixture archives, SQLite, logs containing local process paths or browser binaries. Screenshots remain local evidence: verified-desktop.png, desktop-1440.png, desktop-1920.png, mobile.png. They were inspected visually; panel hierarchy, labels and desktop layout are legible with no overlap.

Remaining: precheck is manifest SHA-256 consistency only, not JSON/audit-chain/authenticity/import success. ZIP resource budgets, import transaction rollback, production authentication and full Unity interoperability are not accepted here. Complete-service regression was not rerun by this independent slice test; parent reports aggregate results separately.

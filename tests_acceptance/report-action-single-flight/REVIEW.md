# Report action single-flight — development regression

Base: integration/ui-review-series 3edb1a55bc60fdaa13980e84597da2f357663231.
Only ReportPage and synthetic regression/records changed; no media/backend merge.

Confirmed offline defect: two calls to the current ReportView.onExport before a
saving-state render dispatched two export requests. New regression on unchanged
base failed with actual 2 versus expected 1. Existing refresh tests exercised one
mutation per scenario and did not cover this event window.

Fix: ReportSession claims a synchronous ref in perform before setting React busy
state, releasing on settlement. Existing session/identity/denial checks remain.
GISIS validation checks the same lock before incrementing its request counter,
so a suppressed action cannot invalidate the running validation. No render-phase
ref mutation, queue, timeout unlock or automatic retry introduced. An explicit
later action after settlement retains the pre-existing behavior; no claim that a
failed request did not execute. This is one mounted session's single-flight guard,
not backend idempotency, cross-tab or multi-user consistency.

Reviewed commands executed from web with existing dependencies (no installation):

- node tests/report-action-single-flight.test.cjs: 3 scenarios passed after fix;
  success, ordinary error, and context change. Actual parent callbacks compiled
  by esbuild; synthetic render/commit/cleanup, API and deferred Promises. Allowlist
  imports; VM has no fetch. Repeated calls before render/while pending dispatch
  once; explicit later calls work; old-case callback does not dispatch.
- node tests/report-refresh-section.test.cjs: existing 12 synthetic scenarios
  passed, with completion marker. Not a complete UI suite.
- ./node_modules/.bin/tsc -b --force: passed.
- ./node_modules/.bin/vite build: passed (installed Vite 8.3.8); existing large
  chunk warning remains, largest JS approximately 1.87 MB before gzip.

An initial command used an incorrect working-directory prefix and did not create
or run the test; corrected before the actual baseline reproduction. No forbidden
operation was attempted. No browser, real React reconciliation, HTTP/backend,
actual export/download, permission probe, seed/data/model or paused test ran.
The callback regression does not prove how a particular browser batches real
clicks; it establishes production handler protection independent of rerendering.
No independent acceptance yet. No production/visual/full-CI claim, merge or deploy.

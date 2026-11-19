# Report explicit case boundary — developer verification

Base: c278933566245ce159b4fad1cc759aae3b1e79c5; same candidate/case-workspace-flow branch.

Report-only compatibility change: missing, empty, whitespace-edged or duplicate case parameters (even identical duplicates) now require explicit selection in the lobby. No default report or first-value fallback. Layout does not mount the report Outlet or start metadata reads; standalone ReportPage also does not mount ReportSession. Navigation, Layout and ReportPage share explicitCaseId. This validates a URL declaration, not existence or access permission.

Valid explicit case IDs retain report/reportId, template and lang behavior; no query rewriting on load. Sidebar report links explicitly encode even a default-shaped case ID. Invalid report sidebar links lead to lobby instead of silently selecting a case. Other page fallback compatibility remains unchanged. Existing report edits/selection logic is unchanged; this does not add draft persistence across navigation or cancel already dispatched requests.

Offline developer commands (web/, reused existing dependencies, no installation):
- node tests/report-explicit-case.test.cjs
- node tests/report-action-single-flight.test.cjs
- node tests/report-refresh-section.test.cjs
- node tests/run-case-workspace-flow.cjs
- ./node_modules/.bin/tsc -b --force
- ./node_modules/.bin/vite build

All passed. Vite retains the large chunk warning. New test invokes actual Layout/ReportPage functions with controlled render/commit/cleanup, synthetic memory read stubs and a forbidden network function. It checks invalid no-read/no-Outlet paths, encoded ID/history, explicit synthetic demo shape, valid→invalid→other identity/case, lobby and sidebar report links. Old base Layout substituted in the same harness fails the invalid-path Outlet assertion (true vs false). This is an isolated frontend counterexample, not backend behavior.

Adjacent 3 single-flight and 12 refresh scenarios retain their assertions; their allowlists now load the actual pure caseContext module. Navigation test uses actual React SSR. Counts are not full coverage and are not added together.

No browser, actual React reconciliation/concurrent scheduling, HTTP/backend, real identity, permissions or real materials tested. No seed/model/application startup. No paused tests run. No changes to API, authorization, main, handoff branch or deployment.

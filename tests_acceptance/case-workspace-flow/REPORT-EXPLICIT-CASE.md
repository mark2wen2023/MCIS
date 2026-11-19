# Report explicit case boundary — developer verification

Base: c278933566245ce159b4fad1cc759aae3b1e79c5; same candidate/case-workspace-flow branch.

Report-only compatibility change: missing, empty, whitespace-edged or duplicate case parameters (even identical duplicates) now require explicit selection in the lobby. No default report or first-value fallback. Layout does not mount the report Outlet or start metadata reads; standalone ReportPage also does not mount ReportSession. Navigation, Layout and ReportPage share explicitCaseId. This validates a URL declaration, not existence or access permission.

Valid explicit case IDs retain report/reportId, template and lang behavior; no query rewriting on load. Sidebar report links explicitly encode even a default-shaped case ID. Invalid report case-scoped sidebar links lead to lobby instead of silently selecting a case; global/non-case-context links retain their original paths without a case parameter. Other page fallback compatibility remains unchanged. Existing report edits/selection logic is unchanged; this does not add draft persistence across navigation or cancel already dispatched requests.

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


## Narrow sidebar correction after independent review

Base 24bcda416d6c1be19420a8b895cc147ea36b3a3c incorrectly redirected every sidebar item on an invalid report URL. The only product change here is to restrict that redirect using existing supportsCaseContext; no route definitions or access rules change. In particular /knowledge remains /knowledge. Existing non-case-context sim/ecfc links also preserve their original paths; this does not assert that those modules are case-aware or tested.

The same controlled-hooks script now loads the actual route table and checks all sidebar destinations: global paths without case parameters, invalid case-scoped destinations to /lobby, valid case destinations using existing encoding rules, and explicit report case even for the synthetic default-shaped ID. Before the correction it failed with /lobby != /sim; after correction it passed, including knowledge. A pending synthetic metadata response released after an invalid duplicate-case transition does not restore the old title or Outlet and starts no new read. No real network or React reconciliation.

Developer reran the four Node commands above, TypeScript and Vite successfully (existing chunk warning). No browser/backend/permission testing, no case/seed/media/model access; no new API or change to report no-read/no-Outlet guards.

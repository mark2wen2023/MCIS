# Retained work: asynchronous response scope
Base: f49218243c3b4cf5842d27e92fa8b253bf152fe9.

Actual page/useLoad in a synthetic hook/router/deferred-response harness reproduced late RUN-A draft replacing the retained draft after navigation to RUN-B. The baseline failed that exact assertion. No service or browser was called.

Draft and comparison requests now have independent latest-request counters in the version session; effect cleanup invalidates requests on session departure/version change. Stale success/error responses do not alter retained work or emit new feedback. Existing draft/comparison is not cleared. This is UI response suppression, NOT cancellation of backend execution or proof of no commit. No automatic retry.

The page explicitly states the draft API uses the service current ledger, not the selected run. Evidence: reports/router.py colreg_draft accepts options rather than a runId; reports/service.py create_report calls sources.build_sections, whose COLREG citations use active_id/current checks. We do not add invented version provenance. Existing comparison base/other IDs remain unchanged. Retained content note warns that ignored responses may still have created a report and directs manual report checking.

Developer commands from web, existing dependencies:
- node tests/colreg-async-work.test.cjs: 8 assertions passed (cross-session delayed draft/compare; out-of-order drafts/comparisons; stale draft error; stale comparison error and retained result).
- node tests/colreg-retained-work.test.cjs: passed.
- node tests/colreg-version-transition.test.cjs: 5 assertions passed.
- node tests/colreg-report-link.test.cjs: 9 scenarios/12 assertions passed.
- npm run build: passed with existing large chunk warning.

No paused/refusal/security probes, real data, models, browser or backend mutations. Harness simulates hooks/effect cleanup, not real React reconciliation. No production identity, full CI or independent acceptance claimed. Evaluation/activation flows and concurrent backend writes are not certified. Requests can finish on the server after UI invalidation. Refresh/off-page state remains memory-only. Previous frozen manifests are historical; new hashes accompany this change.

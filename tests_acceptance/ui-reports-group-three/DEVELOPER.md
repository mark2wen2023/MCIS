# UI report group three — DO NOT MERGE / pending independent acceptance

Exact main base (94d5e38), two source heads and tested merge are recorded in inputs.json. Sources: fix/report-review-pending-input (0a6d0bd) and fix/gisis-stale-validation (16f159b). Both are ancestors. PR104 and UI groups one/two are NOT integrated.

ReportView.tsx is shared: ReviewDialog busy input guards and GISIS props/panel changes occupy separate regions. Git merged without functional conflict. Combined ReportView compared with GISIS head has exactly the added/removed lines of the review-input patch against main (ignoring offsets). ReportPage and all other non-document source files equal their original input blobs. Only REQUESTS.md and ROADMAP.md had append conflicts; original main prefix plus both exact append tails are preserved in input order. No extra functional changes were made.

## Developer verification

All four individually reviewed scripts passed; none failed/skipped. Exact commands/output in selected-results.json, run from web/:

- node tests/report-review-pending.test.cjs: 2 synthetic flows / 14 assertions.
- node tests/gisis-stale-validation.test.cjs: 4 synthetic flows / 44 assertions.
- node tests/gisis-parent-validation.test.cjs: 4 synthetic deferred callback flows.
- node tests/gisis-feedback-scope.test.cjs: 3 synthetic callback flows.
- npm run build: TypeScript and Vite 8.3.8 passed; 766 modules; JS 1,857.50 kB / gzip 600.08 kB. Existing >1500 kB chunk warning remains.

Existing installed dependencies reused; no fresh install. Counts overlap previous runs and must not be added as unique/full coverage. Actual component/session code is evaluated with synthetic hooks, props and deferred responses; parent harness skips startup effects and replaces ReportView. This is not full page integration, DOM/browser, real backend or production identity validation.

## Unverified and preserved boundaries

- Combined independent acceptance, real browser/visual/accessibility, real HTTP/backend and full CI remain pending.
- Review input protection is tested after busy render; pre-render queued events and parent successful dialog closure are not dynamically tested. Drafts remain memory-only; cross-page retention and unknown server commit are not guaranteed.
- Ordinary GISIS late success/errors and feedback isolation are covered synthetically. 403 handling and structured validation-error mapping were inspected statically only, not executed. Production permission equivalence is unverified; permissions were not changed.
- No backend version guarantee, cancellation, safe retry or persistence is added. An ignored result may already have been processed/downloaded; unknown guidance is retained. Full audit refresh and ordering against other operation feedback remain outside coverage.
- PR104 changes report files and needs separate exact-head integration review. This candidate does not include its report-source/export repairs or claim their validation.
- No paused/security/write-refusal tests, models, real records, services or browsers were run. Archive safeguards and main are unchanged. Do not merge or deploy.

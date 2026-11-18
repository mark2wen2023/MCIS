# Report section after refresh — developer synthetic evidence, pending independent review

Base: integration/ui-pr104 `9cc3ecee7251b6f19a739c14ce316740c048594e`.
No other candidates/isolated source-preparation drafts are included.

Confirmed issue: selecting the second section, saving a review, then the parent's keyed
ReportSession refresh destroys selectedSection. Startup picks the first section. New test
on unchanged base failed `save: 'first' !== 'second'` at the post-remount assertion.

Change: parent retains only reportId/sectionId for its exact query+identity context when a
successful operation requests refresh. The freshly loaded document must match reportId and
contain sectionId before the selection is used. Query or identity changes discard this hint.
Exports use the same refresh hint. Original remount, access checks and stale-request handling
remain. No report text, form draft or backend state is persisted by this mechanism. This fixes
section continuity, not all possible draft loss, feedback reset or navigation issues.

Reviewed and executed commands from web (existing node_modules reused, no installation):

- `node tests/report-refresh-section.test.cjs`: 7 synthetic lifecycle scenarios passed after
  fix. Actual ReportPage/ReportSession code, synthetic hooks/effect cleanup/key remount and API.
  Review-save and report-export retain second section. Removed section, case/report/identity
  change and unpinned latest-report replacement fall back to first valid section. One mutation
  only. Test fixture refined to make latest-report scenario unpinned and response case match
  current query; final exact test rerun passed. No browser or real downloads/backend involved.
- `node tests/gisis-parent-validation.test.cjs`: 4 existing synthetic deferred ordinary
  callback flows passed (validate/export with unchanged or changed fields). File statically
  reviewed; no denial/security/write probes invoked.
- `npm run build`: TypeScript and Vite8.3.8 passed, 767 modules; 1,862.53kB JS, gzip601.80kB.
  Existing >1500kB chunk warning. Final change after build only refined test fixtures, not product.

No paused tests, refusal probes, HFACS, models, real records, service/browser, source-isolation
scripts or production dirs executed. No full CI, browser visual/accessibility, actual network
save/reload, identity authentication, concurrent actions or production acceptance claimed.
Counts are separate evidence types, not full-suite totals. DO NOT MERGE or deploy.

## Follow-up: click event and pending-operation selection (2026-11-18)

Exact parent: `2f2bba3810a4c147071ff69f21464e848250a5eb`.
Independent review identified two remaining defects. Before this product change,
`node tests/report-refresh-section.test.cjs manual` failed first != second, and
`node tests/report-refresh-section.test.cjs race-save` failed second != first.
The test now invokes actual ReportView button handlers with a synthetic click event
and section-chip clicks while deferred API callbacks are pending.

Refresh now discards click arguments explicitly. A synchronously updated section ref
preserves the latest user selection when review/PDF/GISIS export resolves, rather
than the section captured before the request. Refresh and export notice updates
check the current session; old-case save cannot refresh the new session.
No backend or permission behavior changes, and section navigation remains available.

Reviewed exact developer commands from web:
- `node tests/report-refresh-section.test.cjs`: 12 synthetic scenarios passed,
  including original 7, actual refresh callback, delayed review/export/GISIS, and
  case switch during pending review. These replace, not add to, the original 7.
- `node tests/gisis-parent-validation.test.cjs`: 4 adjacent synthetic flows passed.
- `npm run build`: TypeScript and Vite passed; 767 modules, JS 1,862.59 kB,
  gzip 601.84 kB; existing large-chunk warning remains.

Synthetic hooks/API are not React browser scheduling, real HTTP, downloads,
production identity or visual acceptance. Follow-up independent review pending.
No paused tests, refusal probes, real data, models, HFACS or browser executed.
The original frozen hash record documents the parent; follow-up inputs are in
`logs/report-refresh-section-r2-impl-hashes-frozen.txt`. No merge/deploy.

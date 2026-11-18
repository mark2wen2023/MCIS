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

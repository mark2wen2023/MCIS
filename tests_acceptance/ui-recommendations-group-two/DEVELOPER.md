# UI recommendations group two — DO NOT MERGE / pending acceptance

Exact base, two source heads and tested merge are in inputs.json. Sources are fix/recommendation-missing-citation (8d4c86a) and fix/recommendation-transition-note (92265a9). Both are ancestors of this candidate. Main remained 94d5e38 at preparation. UI group one and PR67 are not included.

Both sources modify RecommendationsPage.tsx, but separate regions: parent missing-reference display versus Detail local input revision counters. Git merged the page without conflicts. Comparing the combined page to 92265a9 reproduces exactly the added/removed lines of 8d4c86a against main (ignoring diff line offsets). All other source files match their input blobs. Only REQUESTS.md and ROADMAP.md conflicted: main prefix and each branch's complete append were preserved byte-for-byte, in input order. No additional functional edits or tests were introduced.

## Developer verification

Reviewed and ran only these commands from web/ (exact results in selected-results.json):

- node tests/recommendation-missing-citation.test.cjs — 6 synthetic states / 10 assertions passed.
- node tests/recommendation-transition-note.test.cjs — 5 synthetic completion scenarios passed.
- node tests/recommendation-form-save.test.cjs — 10 synthetic reply/progress scenarios passed.
- npm run build — TypeScript and Vite 8.3.8 passed, 766 modules; JS 1,856.81 kB (gzip 599.86 kB). Existing >1500 kB chunk warning remains.

Three selected scripts passed, none failed/skipped. Counts are not added to historical runs as unique coverage. Existing installed dependencies were reused, not freshly installed. Test code evaluates actual page/Detail/useToast with synthetic hooks, board data and deferred responses. It inspects current rendered input representations, not a real browser DOM. No HTTP service, production permissions, real data or model was exercised. No paused/security/write-refusal tests were run.

## Limits and follow-up

Pending independent combination, browser/visual, cross-page lifecycle, backend and production-identity/permission acceptance. Local drafts remain in page memory. No backend concurrency, cancellation, safe retry or persistence guarantee is added. Missing-reference text means absent from the loaded current board, not proven deletion/permission denial or verified historical version. Initial loading/error and manual card selection are covered synthetically; all later request races are not certified. Detail tests do not certify the full parent reload/unmount lifecycle. Prior source notes and freezes remain historical; use this candidate's combined page freeze for review. PR67 overlaps this page and remains a separate integration task. Main, permissions and archive protections are unchanged; no deployment or merge approval is implied.

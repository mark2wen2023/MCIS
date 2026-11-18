# Observed A → B → A draft binding

Base: 23d347a6df90edec6d1ec6f1934c6865836f759f. Developer synthetic verification;
not independent acceptance, real React concurrent rendering, browser, HTTP or server revision control.

Before fix the new continuous-render test failed: after observing B then returning all compared
fields to A, the draft source-change notice disappeared (false, expected true).

Detail now tracks a local monotonically increasing observed-content generation. A ready source
change advances it; equal source rerenders do not. Drafts bind source and generation; adoption
explicitly binds current generation while preserving note. Unknown remains locked. Existing
parent refresh epoch remains in place. No backend, permissions or shared-hook changes.
The counter is page-memory only and cannot detect server changes never read by this page.
Ref updates during these synthetic renders do not establish concurrent React scheduling safety.

## Commands executed from web

- `node tests/recommendation-observed-source.test.cjs`: 4 synthetic scenarios: actual parent
  refresh A/B/A with a draft; equal-content rerenders; unknown lock; source changes without a
  refresh in the fixture to isolate generation checks from the existing refresh epoch.
  The last is a component contract test, not evidence of a separate production update path.
- `node tests/recommendation-reload-action-window.test.cjs`: 3 scenarios passed.
- `node tests/recommendation-progress-snapshot.test.cjs`: 5 scenarios passed.
- `node tests/recommendation-progress-flight.test.cjs`: 7 scenarios passed.
- `npm run build`: TypeScript/Vite passed, existing >1500kB chunk warning.

Actual parent/Detail code is bundled against synthetic hooks, loader results and Promise/API
stubs. Tests inspect newly rendered input values, preserve draft through loading/failure,
block old callbacks, and verify explicit adoption then ordinary synthetic save.
Counts are separate suites, not a full test total. No actual request or backend test ran.
No fresh dependencies, browser, models, HFACS, paused/refusal/security tests, real cases or
seed reads. No production claim, merge or deployment. Pending independent review.

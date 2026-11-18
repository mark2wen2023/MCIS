# Explicit adoption of observed progress — developer evidence

Base ba7e59e366e8c52a84c30f536737de9cef0816e2; independent branch
fix/recommendation-progress-adopt. Before product fix, new note-only test invoked
save after snapshot25→50 and observed sent.length=1 instead of0. Synthetic callbacks
only; no real write occurred.

Progress saving now checks known source change and read readiness in both button
and callback. Parent supplies board loading/error readiness. A ref compares captured
source with latest rendered source and existing session lifetime, suppressing obsolete
adoption/save callbacks. Explicit adoption sets only local percentage/source binding,
increments edit counter, preserves note, and sends nothing. Loading/error, non-Responded,
pending save and unknown prevent adoption; unknown lock is never reset by adoption.
Same-percentage note remains unsaved and explicitly cannot be saved alone by this API.
No old-value override action added. User must adopt, then deliberately edit and save.
This changes only progress controls, not other recommendation operations.

This is local observed-field comparison, not server CAS or read proof. Source fields
(id/progress/status/updatedUtc) may not distinguish all histories/ABA. Another user can
modify after read. No immutable snapshot/revision receipt or multi-user guarantees.
Loading/error guards reflect parent state rendered into Detail; browser scheduling is
not independently verified. Drafts/locks remain in memory and do not survive unmount.

Reviewed exact commands from web, existing dependencies:
- node tests/recommendation-progress-snapshot.test.cjs: 5 continuous synthetic cases
  passed (extends previous4, not additive). Covers clean update; edited source; note-only
  stale submission blocked; unknown; pending save. Actual parent/Detail, synthetic hooks
  and read snapshots. Both button disabled state and direct callbacks are exercised.
  Loading/error adoption blocked; source50 callback ignored after source60; unmount
  callback ignored. Explicit adoption retains exact note and sends0; manual change65
  then explicit save sends one request with note. Unknown/pending never re-dispatch.
- node tests/recommendation-progress-flight.test.cjs: 7 passed.
- node tests/recommendation-form-save.test.cjs: 10 passed.
- node tests/recommendation-read-state.test.cjs: 5 passed.
- npm run build: TypeScript/Vite passed, 768 modules, JS1867.00kB/gzip603.34kB;
  existing large-chunk warning remains.

No browser/visual, real HTTP/backend, permissions/denial tests, real data/seeds, models,
HFACS, paused nodes or write-refusal probes. Existing backend checks unchanged.
Independent review pending. No merge/deploy.

## Follow-up: isolate source comparison from read-failure gating (2026-11-18)

Base7702e62aca3f30a209bb01d76161bc369181af9d; test-only branch
 test/recommendation-adopt-source-guard. No product code changed.
Independent review correctly found that previous source50→source60 test updated parent
props but did not render Detail before invoking old adoption. The latestProgress ref
could still contain readReady=false from the previous failure render. That pass did
not specifically establish that source comparison blocked the callback.

The test now renders Detail at ready/source60 FIRST, asserts readReady=true, current
percentage60, and a non-disabled current adoption button, then invokes source50's old
adoption callback. Original draft percentage and exact note remain, with zero requests.
For edited mode it also captures an originally enabled save at source25/draft35,
then invokes that old save after ready/source60 Detail render; dispatch remains zero.
Thus the old-save check is not an already-disabled equal-value or sourceChanged closure.
Normal current adoption/save remains covered by the note-only path.

Reviewed commands from web:
- node tests/recommendation-progress-snapshot.test.cjs: strengthened5 passed;
  rerun after adding old-save assertion, still5 (not extra additive cases).
- node tests/recommendation-progress-flight.test.cjs: adjacent7 passed.
- npm run build: TypeScript/Vite passed,768 modules,JS1867.00kB/gzip603.34kB,
  existing chunk warning. Build preceded final test-only old-save assertion; product
  unchanged throughout this follow-up.

Not covered: source A→B→A with identical observed fields, or reload invocation to
Detail rerender window. These are not closed by this evidence. No server version
control, multi-user consistency, browser scheduling/visual or real HTTP claim.
No backend/security/refusal/paused tests, model, seed/case reads or real data.
Independent review pending; no merge/deploy. Follow-up freeze:
logs/recommendation-adopt-source-guard-test-hashes-frozen.txt.

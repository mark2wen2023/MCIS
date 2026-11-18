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

# Registered preview: pin displayed source versions

The workbench already discarded stale requests after case, identity or manifest changes.
It did not, however, compare returned CSV snapshot SHA-256 to the manifest version
visible when the user clicked calculate. If the server's current registered bytes
changed without a UI refresh, a result for the newer bytes could previously display.

## Change
- Before dispatch, each chosen ID must resolve to exactly one eligible current-case
  local-intake candidate with valid SHA, not Mismatch or needsReview.
- Capture those ID/SHA pairs for that invocation.
- The existing strict response parser additionally rejects source snapshots whose
  hashes differ from the captured pairs. No result is displayed; refresh/recheck is
  requested. Existing cancellation/context invalidation remains in force.
- Parser pin argument is optional for legacy callers; the investigator workbench
  always supplies it. Wire request and server behavior are unchanged.

This is fail-closed frontend version consistency, not a backend compare-and-swap,
atomic lease, durable receipt, independent corroboration, semantic validation,
manual approval or production authentication. A hash does not validate content.
No report export or review write path is introduced.

## Verification
Primary source-version.test.tsx: 59 local HappyDOM/controlled-fetch assertions,
including prior 53 (overlap, not 59 new). Covers changed response hash suppression,
refresh notice, exact pin match, missing/wrong-ID/wrong-hash pins.
Original registered-independent.tsx: 53 regression assertions pass.
TypeScript/Vite production build passes; existing bundle-size warning remains.
Independent review results appended after verification.
No new live backend, real browser, LLM or CI claim. No merge/deployment.

Independent reviewer: source-version-review.tsx 71 checks pass (prior53 + new18).
Includes stale manifest/new response rejection, fresh manifest/new SHA success,
duplicate/foreign-case/review-required/Mismatch/invalid-SHA candidate refusal.
Independent regressions53/48/15/57 pass (overlapping). Duplicate-key React warning
is observed only on deliberately duplicated manifest fixture; request fails closed.
Targeted lint exits0 with three existing warnings (control regex, two effect setters).
Implementation and independent review are native subtasks, not Codex app runs.

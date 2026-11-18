# Recommendation pending operation lifetime — developer evidence

Base: 80b0756d583cb27a2caa4cccf879f4aecfa564b8 (includes independently reviewed
report refresh fix); independent branch fix/recommendation-pending-context.
Product recommendation file remains based on integration/ui-pr104 9cc3ece.
No separate body-CAS/create-unknown candidate is incorporated.

Reproduction before product change: the new parent test failed with pending=null
instead of Implemented when A's delayed transition completed after B confirmation
was opened. The actual parent drop/transition handlers are invoked with synthetic
records and deferred promises, not a real server or browser.

Fix: pending confirmation is cleared only if it is the exact captured object.
Each new drop creates a new object, so A→B→A is also distinct. Parent refresh and
pending clearing check local mounted/identity lifetime. Local action notifications
and Detail reply/progress completion effects are ignored after lifetime expiration.
Existing edit counters and draft preservation remain. Global Toast is unchanged;
CreateForm and ConsultationPanel are not expanded into this fix.
This is display guarding, not cancellation, remote rollback or proof of non-submission.
No automatic retry, permission or backend changes. Concurrent writes are not serialized.

Reviewed and executed from web with existing dependencies (no install):
- node tests/recommendation-pending-context.test.cjs — 14 synthetic cases passed:
  transition normal/A→B/A→B→A/unmount, each success and ordinary transport failure;
  actual Detail reply normal/A→B/unmount, each success and ordinary transport failure.
  Case departure is modeled by executing registered effect cleanups, not router/browser
  navigation. Parent pending and reload callbacks remain actual. The synthetic A→B
  reply test keeps the old Detail callback alive to exercise the parent identity guard;
  real keyed Detail also unmounts on selection change. No security/denial cases.
- node tests/recommendation-transition-note.test.cjs — existing 5 cases passed.
- node tests/recommendation-form-save.test.cjs — existing 10 cases passed.
  Existing assertions unchanged; added mount hook and ApiError test dependencies.
  An initial run exposed missing ApiError in the fixture, corrected before final rerun.
- npm run build — TypeScript and Vite8.3.8 passed, 767 modules; JS1863.01kB,
  gzip601.98kB; existing large-chunk warning remains.

These counts are distinct selected synthetic cases, not full-suite acceptance.
No browser/visual, real HTTP, production authentication, models, HFACS, real data,
paused nodes or write-refusal probes. No source-isolation draft executed.
Independent review pending. Do not merge or deploy.

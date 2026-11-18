# Current-page progress single-flight — developer synthetic evidence

Base 1a01a494c0428557c60d07833fcf6da542ac2b5a, including 80b0756.
Branch fix/recommendation-progress-flight. No other candidate integration.

Before fix the new synthetic test failed: second click before rerender sent 2 PATCH
requests instead of 1. Actual Detail callbacks are used, with synthetic hooks/API
and deferred Promise, not a browser or service. No backend tests executed.

A synchronous ref locks progress submission before any await or rerender. The
button also shows disabled state while sending/unknown. Inputs remain editable;
existing revision counters preserve newer note/percentage edits, including ABA.
Successful completion explicitly distinguishes submitted progress from newer unsaved
input. Success text no longer asserts a new audit event for every response: the
existing backend may return unchanged progress without writing an event.
Any caught failure conservatively keeps the lock and input, displays unknown result,
and asks the user to copy the draft and check current record/audit. No automatic
retry or claim of rollback/non-submission. Even a refresh exception after successful
PATCH is treated conservatively. Session expiration suppresses display effects.

Only current mounted Detail progress requests are serialized. This is not durable
idempotency or multi-user/tab consistency. Leaving/remounting loses this in-memory
lock and draft; it must not be used to infer that an earlier request did not commit.
Other mutation types, response schema validation and backend version comparison
are outside this change. No production permissions or API contracts changed.

Reviewed commands from web using existing dependencies, no installation:
- node tests/recommendation-progress-flight.test.cjs: 5 cases passed. Each checks
  double click before rerender, disabled pending button and direct callback reentry;
  cases: normal success, newer percentage, ABA input, ordinary transport failure
  with newer input and blocked repeat, session cleanup before completion. Reads
  current rendered inputs; no denial/security cases. Final test-only strengthening
  of pending-button assertions reran these 5 after build.
- node tests/recommendation-form-save.test.cjs: existing10 passed.
- node tests/recommendation-pending-context.test.cjs: existing14 passed.
- node tests/recommendation-transition-note.test.cjs: existing5 passed.
- npm run build: TypeScript/Vite8.3.8 passed, 767 modules, JS1863.72kB,
  gzip602.26kB; existing large-chunk warning.

Corrected prior test header references from useToast.run to useScopedActions.run.
Counts describe selected developer synthetic evidence, not independent/full-suite
acceptance. No browser, HTTP, backend tests, real data, models, HFACS, paused nodes
or write-refusal probes. No merge/deploy; independent review pending.

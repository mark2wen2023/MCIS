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

## Follow-up: synchronous refresh callback failure (2026-11-18)

Parent 2e3f3ad38f75f847c53ee604e1de9825a4b5b158. Independent review found
note clearing preceded onChanged. New frontend-only synthetic callback throws after
successful mock PATCH; before product fix the current input was empty instead of
submitted text. This is not backend fault injection or a real service failure.

Move clearing after normal onChanged return and recheck current lifetime/edit revision.
A synchronous throw leaves original or newer note intact and the unknown lock retained.
Success copy explicitly says reload requested, readback not confirmed. Unknown copy
explicitly states no in-place unlock: copy draft and manually check record/audit first.
Neither successful callback return nor asynchronous reload initiation proves readback.
This does not implement reload completion tracking, recovery or a server commit guarantee.

Reviewed/executed commands from web:
- node tests/recommendation-progress-flight.test.cjs: 7 passed (prior5 plus callback
  throw with original note and with newer note); checks current rendered note, callback
  reached once, locked repeat, notices/no unlock, and unconfirmed readback wording.
- node tests/recommendation-form-save.test.cjs: adjacent10 passed.
- npm run build: TypeScript/Vite passed; 767 modules, JS1863.84kB/gzip602.32kB,
  existing chunk-size warning. No further product/test changes after verification.

Developer synthetic evidence only; no backend, browser, real data, paused/refusal
probes, model or HFACS execution. Previous14/5 tests were not rerun this follow-up;
counts must not be accumulated as new coverage. Independent review pending.
Original freeze remains parent evidence; follow-up freeze is
logs/recommendation-progress-flight-r2-impl-hashes-frozen.txt. No merge/deploy.

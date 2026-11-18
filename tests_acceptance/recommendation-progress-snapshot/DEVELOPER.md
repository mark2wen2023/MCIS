# Same-ID progress snapshots — developer synthetic evidence

Base d7447db64694afcef865ea8cdca0f8657fe1e0c1, independent branch
fix/recommendation-progress-snapshot. No receipt design implementation.

Before fix, the new continuous Detail test failed 25 != 50: unchanged slider stayed
at25 after same-ID snapshot updated to50, although save compared against new50.
The product now derives unedited percentage directly from rec.progressPct; first
percentage/note edit creates a local draft bound to observed id/progress/status/
updatedUtc. Snapshot differences preserve the draft and show a source-change notice.
This comparison is NOT a server version token, history proof, or ABA/concurrency control.
Note and percentage share a draft group. Existing edit counters prevent successful
older saves from clearing newer input. Only unchanged successful progress completion
clears its draft; failure/unknown does not. Reading never releases the unknown lock.

Reviewed exact commands from web, existing dependencies, no installation:
- node tests/recommendation-progress-snapshot.test.cjs: 4 continuous cases passed:
  clean, edited percentage+note, note-only, unknown after ordinary transport failure.
  Actual parent rerenders pass props to the same actual Detail state using synthetic
  hook stores and mocked read states. Loading and ordinary failure retain old snapshot;
  ready then supplies same-ID50. Current input and disabled button inspected; unknown
  remains locked after refresh and a direct save callback cannot submit again.
- node tests/recommendation-progress-flight.test.cjs: 7 passed.
- node tests/recommendation-form-save.test.cjs: 10 passed.
- node tests/recommendation-transition-note.test.cjs: 5 passed.
- node tests/recommendation-read-lifecycle.test.cjs: 6 passed.
- node tests/recommendation-read-state.test.cjs: 5 passed.
- npm run build: TypeScript/Vite passed, 768 modules; existing large-chunk warning.
  After strengthening parent handoff and capturing slider value before React state
  updater, exact snapshot/flight/form scripts and build rerun passed. Remaining three
  adjacent scripts passed before that final event-value capture refinement.

Read hook and parent/Detail scheduling are tested separately, not a browser-mounted
end-to-end tree. No real HTTP, backend tests, real data, seed reads, models/HFACS,
paused/security/refusal probes, restore or production identity validation.
Genuine record removal/denial or navigation still may unmount in-memory drafts;
this change only addresses same-ID snapshots and ordinary retained-data read states.
No new persistence or automatic retry. Independent review pending; no merge/deploy.

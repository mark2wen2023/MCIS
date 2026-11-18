# Recommendation read lifecycle — developer synthetic evidence

Base067251e46e970cb9bf45d1e96178ec8118a9aa40 (documentation child of e8ec0bc).
Before product change, `node tests/recommendation-read-lifecycle.test.cjs baseline`
failed stale != null: actual shared hook accepted old success after reload but before
passive cleanup. Initial test module-map omission was corrected before reproduction.
Shared hook is NOT modified. New useBoardLoad is used only by RecommendationsPage,
whose case/query/identity key already remounts sessions. Generation invalidates
synchronously on reload; effect cleanup, layout unmount and identity checks guard reads.
Ordinary failure retains old data explicitly labeled stale; existing403 clearing is
preserved in code, statically reviewed only, no denial test executed.

Page distinguishes initial unread from zero, shows reload/stale/error states, and
labels independent board/audit reads as not one snapshot. Generic audit failure no
longer claims an authorization cause. Old data keeps Detail keyed identity and avoids
remount solely for loading/failure. Existing draft counters/locks unchanged. This
is not a whole-page draft persistence guarantee; genuine missing records/denial may
still remove Detail. Old snapshot actions still have existing backend checks; this
change does not supply server version control or atomic board/audit snapshots.

Reviewed exact commands from web, existing dependencies only:
- node tests/recommendation-read-lifecycle.test.cjs: 6 synthetic hook cases passed:
  consecutive reload before cleanup with late success/error; retained data on ordinary
  refresh failure; initial failure; identity change without reload; unmount without reload.
  New request then succeeds in the late-response cases. Effect scheduling is synthetic.
- node tests/recommendation-read-state.test.cjs: 5 page states passed; current unread
  metrics absent, stale/error notices and Detail key retained. Does not mount a full DOM.
- node tests/recommendation-progress-flight.test.cjs: 7 passed.
- node tests/recommendation-pending-context.test.cjs: 14 passed.
- node tests/recommendation-form-save.test.cjs: 10 passed.
- node tests/recommendation-transition-note.test.cjs: 5 passed.
- node tests/recommendation-missing-citation.test.cjs: 6 states/10 assertions passed.
  Existing test mappings now point to local hook; citation fixture gets the layout/ref
  hooks introduced by previous scope guards, assertions unchanged.
- npm run build: TypeScript/Vite passed, 768 modules; JS1865.37kB/gzip602.77kB,
  existing large-chunk warning. Later changes only strengthen hook tests and repair
  citation fixture; both exact scripts rerun after build, no product change.

No real HTTP, browser, cases/seeds, models, HFACS, paused nodes or refusal probes.
No backend tests or security assurances. Independent review pending. No merge/deploy.

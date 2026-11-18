# First UI group — DO NOT MERGE / pending independent and browser acceptance

Developer integration verification only. Exact base, five inputs, tested merge and matching source blobs are in `inputs.json`. No additional functional changes were made during integration. All five inputs are ancestors. Only REQUESTS.md and ROADMAP.md conflicted: each original main prefix plus every source append was retained byte-for-byte in input order. All other changed files equal their source input blobs. Other UI, media, report and Pi candidates are excluded.

## Executed verification

From `web/`, exact commands and outputs are in `selected-results.json`: 12 explicitly reviewed synthetic test scripts passed, no failed/skipped scripts. Counts of scenarios and assertions differ and are not summed into a full-suite count. Actual components with synthetic hooks/API stubs, pure routing and SSR are used; no real HTTP or browser. No paused/security/write-refusal tests were run.

`npm run build` passed (`tsc -b && vite build`, Vite 8.3.8, 767 modules). Output JS 1,859.61 kB, gzip 600.89 kB; existing >1500 kB chunk warning remains. Existing installed dependencies were reused; no fresh installation, model, real data or service execution. Build output/node_modules are not delivered.

## Remaining boundaries

- Combined tests/build are developer evidence, not independent combination acceptance, complete CI or visual/browser testing.
- Case metadata loading status does not establish service health or authentication; complete identity/lobby transitions are not certified.
- Toast structure is not assistive-technology verification; repeated identical messages may not be re-announced. Unmount timer cleanup remains outside this selected coverage.
- Interview report links open current records. Sentence positioning, historical versions, missing-detail behavior and backend isolation are not established by these tests.
- COLREG preserves local draft/comparison across versions and suppresses stale replies. Draft generation still uses current server context, not the selected historical run. Ignoring a reply does not prove generation did not occur; no cancellation/retry guarantee or persistent pending-job recovery. Other evaluation/activation callbacks are not certified.
- Missing analysis scenario shows an explicit exit to baseline rather than silent fallback. Local case/source controls are hidden in this state; real navigation/visual acceptance remains pending.
- No permissions, backend/archive safeguards or main branch changed. No merge/deployment approval is implied.

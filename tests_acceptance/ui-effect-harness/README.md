# UI effect harness correction — developer validation, pending independent review

Base/product source: 08fc47b5c5f1b456e84b6b64fe41ac26f32647c5.
Comparison source: 49fc5b06ebedd2229b028c12f810180c8aef4649.
Only three test harnesses changed; no product changes. Integration branch remains unchanged.

## Diagnosis
Report harness incorrectly ran parent cleanup during keyed child replacement and ignored effect dependency updates. Snapshot harness only ran layout effects on mount; the unresolved scenario could exit 0 without the final completion message. Composite rerun exposed the same dependency defect in reload-action-window. Effects now queue during component evaluation, commit afterwards, and clean up before replacement; keyed report cleanup is scoped to the child store. All original business assertions remain. beforeExit fails incomplete scenario loops.

The updated three scripts pass against BOTH original source and candidate: report 12 scenarios, snapshot 5, reload window 3. Baseline used a separate frontend-only copy with the three changed product files replaced by their exact 49fc5b0 blobs. This supports a harness defect, not a demonstrated product regression.

## Exact bounded regression
results.json records commands, exit codes and output: 24 Node scripts (including SSR), their two esbuild preparations, TypeScript and Vite all passed. Each Node command produced its completion output. Separately, node tests_acceptance/ui-commit-phase/check.cjs passed its three synthetic groups. Counts are separate selections, not additive full-suite coverage.
All web commands used a no-fetch preload containing:
`globalThis.fetch=()=>{throw Error('network forbidden in synthetic validation')};`
Existing dependencies reused, no installation. Vite retains its >1500 kB bundle warning.

## Limits
Synthetic function/hook lifecycle models, not actual React scheduler, browser, visual, HTTP or production identity acceptance. Layout/passive scheduling is simplified; no real concurrent rendering proof. No backend, seeds, real materials, models, HFACS, paused tests or write-denial probes run. No merge or deployment. This candidate awaits independent review before any integration branch update.

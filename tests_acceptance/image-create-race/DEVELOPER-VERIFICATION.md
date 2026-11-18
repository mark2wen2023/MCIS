# Image import response guard
Base: 1d49f557204ed6a986539093c1b635413f176705.
Five new ordinary nodes statically reviewed: synthetic DOM and delayed successful HTTP doubles; no files, database, browser, model or security/write-refusal probes.
Baseline: 4 failed, 1 passed. Import overwrote edits and accepted selection changes (case/run/away-back).
After fix: `node --test tests_acceptance/image-create-race/page.test.cjs`: 5 passed. Targeted image-read-race 5 and image-save-context 4 passed using their existing documented patterns. All developer-side; not independent or real backend acceptance.
Captures edit/selection epoch and IDs; stale response preserves input and says creation may already have occurred, requiring manual result checking. No automatic retry or cancellation claim. Permissions/archive unchanged; drafts still memory only.

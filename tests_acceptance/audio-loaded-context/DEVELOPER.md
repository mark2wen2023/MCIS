# Loaded/target audio context — developer synthetic regression

Base: baabeed48bf59c322f77dfdc91ed262500843ab8.
The previous page changed the run field via open-task without invalidating/labeling the retained
source areas. Manual input cleared the new declaration but left the raw metadata. The new shared
notice explicitly identifies the loaded case/run and the not-yet-loaded target. Both source areas
remain with the loaded record and drafts are retained. Successful accepted loading updates both.
No HTTP contract, permissions, model execution, archive behavior or original bytes changed.

Before execution the new test was reviewed: only Node built-ins, one HTML source read, synthetic
DOM, in-memory records and controlled Promises. json() is replaced by memoryRequest; real fetch
always throws and zero calls are asserted. No audio, Python, seed/case files, service or browser.
The first red run encountered a missing synthetic notice element; the assertion was corrected
to treat absent notice as empty. The second pre-fix run failed all four scenarios at the waiting/
selection notice assertion, after confirming metadata still contained A. It did not reach later
failure/success branches. Post-fix tests exercised all those branches.

Exact post-fix command from repo root (14 passed, 0 failed/skipped):
```
node --test tests_acceptance/audio-loaded-context/page.test.cjs tests_acceptance/audio-source-declaration/page.test.cjs tests_acceptance/audio-draft-lifecycle/page.test.cjs
```
Four new cases: open-task B waiting then ordinary failure; accepted B success; B late after manual
selection C; manual selection B. Current DOM draft and dirty checked on retained states. Explicit
confirmation is supplied by a synthetic confirm returning true, so accepted B replaces A as before.
Four source-display cases (one expectation updated to retained-but-labeled), six neighboring draft
lifecycle cases. These are developer results only, not added to earlier independent counts.

Limits: no actual HTTP acceptance, browser/visual/native-confirm behavior, audio playback, identity
or original verification. The notice distinguishes selection from loaded data, not backend current
versions. No new retries, writes, cancellation or provenance claims. No Vite/full-suite build:
standalone HTML change. Application startup/archive and paused/refusal tests remain unexecuted.

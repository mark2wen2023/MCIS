# Image loaded/target context — developer synthetic regression

Base: 4ec789e288dffad7284944ea9e1b9206e4c6f042, candidate/media-demo-launcher.
Task success changes the run selector without loading that run. Previously it replaced the
loaded-run status while leaving old source text, download controls and drafts. Manual changes
also left these areas without a persistent loaded-versus-target notice. The new independent
notice names the loaded case/run and target not yet loaded, and explicitly attributes source,
drafts and downloads to the loaded run. It updates on manual selection, task selection and render.
No permissions, fetching, downloads, mutation, preview or archive behavior changed.

Static review before running: only Node built-ins and one HTML source read. Actual inline
callbacks use a synthetic DOM, json() replaced with controlled in-memory Promises, and a preview
double with only clear available. Real fetch and image decoding throw; zero calls asserted.
No application import, images, cases/seeds, Python, model, browser, service or dependency install.
No paused/refusal tests selected.

Command (repo root):
```
node --test tests_acceptance/image-loaded-context/page.test.cjs
```
Pre-fix: 0 passed / 5 failed at missing ownership notice after verifying retained A source,
draft and dirty. Task scenarios failed immediately after task-selected B; subsequent read
outcomes were reached only after the fix. Post-fix: 5 passed / 0 failed / 0 skipped.

Cases: task successfully selects B, then read pending/failure; accepted B read; B response late
while C selected; manual case change; manual run change. Current DOM draft and dirty are checked
in retained states. Confirm returns true in the synthetic fixture, so accepted B replaces A as
existing behavior permits. New notice survives generic error status. No download is invoked:
its association is a source-level observation and notice assertion, not download acceptance.

Developer results, pending independent review. Not browser layout/native confirmation, real HTTP,
image decoding or original verification. No build/full suite; standalone HTML and five selected
Node cases only. No source truth, cancellation or backend version guarantee. No merge/deployment.

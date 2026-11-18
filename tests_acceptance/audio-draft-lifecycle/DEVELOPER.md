# Audio draft lifecycle — developer synthetic regression

Product/test baseline: 9bc2f3d95db37798cebd0d334d83673e432102ce on candidate/media-demo-launcher.
Test-only addition; no product behavior changed and no new product defect demonstrated.

Static safety review before execution: the test imports only node:test, node:assert/strict,
node:fs and node:vm. Its sole file read is the audio review HTML source. The actual inline
callbacks run against synthetic DOM/player doubles. fetch always throws and each scenario
asserts zero calls. No audio bytes, cases/seeds, Python application, server, models, browser,
external dependencies, paused nodes or write-refusal probes are used.

Exact command, from repository root:
```
node --test tests_acceptance/audio-draft-lifecycle/page.test.cjs
```
First execution: 6 passed, 0 failed, 0 skipped (developer execution, not independent acceptance).

Four edited scenarios cross clear/run change with late play success/failure. Each starts play,
then changes the current textarea and fires its bound oninput while busy. Assertions inspect
current DOM text, dirty, dirtySegments and editVersion before/after the context change and late
settlement. Captured beforeunload callbacks must prevent default and set returnValue. After busy
releases, the actual load callback receives a cancelled confirmation: no fetch, no replacement,
no dirty reset. Two unedited controls check that clearing/changing run does not create dirty or
request a warning; canReplace returns true without confirmation (no actual read is dispatched).

Changing the run field is not a successful new-run load. Accepted replacement and save are not
exercised. This does not verify browser event delivery, native unload prompt display/suppression,
pagehide behavior, media decoding/listening, or backend reads. Inputs are synthetic and only the
textarea edit path is exercised; the other fields share the handler but are not separately tested.
No build or whole-suite rerun: standalone Node test addition, no runtime edits. No totals combined
with earlier suites; no merge/deployment. Application startup/archive tests remain paused.

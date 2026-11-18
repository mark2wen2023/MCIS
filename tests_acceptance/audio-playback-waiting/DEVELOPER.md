# Audio playback waiting feedback — developer synthetic verification

Base: 59559cc7e09614da51a4b8bd6501ca42244a4ac0. Standalone HTML only.
Before play(), display the segment/range and waiting status, explicitly not started/heard.
Current-context rejection ends the waiting message without retry; existing success wording and
late-context suppression remain. Validation errors before play do not claim a play attempt.
No changes to busy, queuing, timeout, stopping, permissions, download or playback policy.
A never-settling Promise still keeps busy; there is no timeout unlock or automatic retry.

Safety review: Node built-ins only, sole file read is HTML source. Actual inline callbacks use
synthetic DOM and controlled play Promise; input oninput is called and current DOM/dirty checked.
fetch throws and zero calls are asserted. No audio, Python, cases/seeds, model, browser, service,
new dependencies, paused nodes or write-refusal probes.

Pre-fix command: node --test tests_acceptance/audio-playback-waiting/page.test.cjs
All 8 failed at missing waiting feedback; later settlement assertions were not reached pre-fix.
Post-fix command from repo root:
```
node --test tests_acceptance/audio-playback-waiting/page.test.cjs tests_acceptance/audio-playback-serialization/page.test.cjs tests_acceptance/audio-playback-late-status/page.test.cjs
```
18 passed, 0 failed/skipped: eight new cases (unchanged/case/run/clear x success/failure), two
serialization and eight late-status cases. New tests inspect pending feedback and a second click,
keep Promise pending for an event-loop turn, then settle manually; no wall-clock timeout claim.
Draft/dirty remain. Serialization failure expectation now checks the explicit ended-wait message
instead of the prior unchanged text. Existing no-queue and explicit later-click checks retained.

Developer synthetic results only; no independent review claimed. Not real browser scheduling,
actual media decoding/listening or accessibility. No Vite/full-suite build for standalone HTML.
Backend startup/archive pause remains (seed import isolation unresolved). No merge/deployment.

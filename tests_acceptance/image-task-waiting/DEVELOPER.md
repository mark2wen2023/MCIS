# Image task query waiting — developer synthetic check

Base fe927430bacd92d875d3d895c5acc1630b2c05c6, candidate/media-demo-launcher.
Only add query-start feedback replacing old task JSON: waiting for query response is not proof
that a task is executing. No request count, generation guard, latest-response priority, polling,
retry, timeout, task state, model, permission or archive change.

Static review before execution: Node built-ins, sole HTML source read, actual inline query
callback and in-memory Promise replacement for json(). fetch throws and zero calls asserted.
Preview clear is a no-op double; no image decode, Python, case/seed material, models, browser,
service, dependencies, paused nodes or refusal probes.

Exact repo-root command:
```
node --test tests_acceptance/image-task-waiting/page.test.cjs
```
Pre-fix 11 failed at waiting assertion with OLD_RESULT JSON still displayed (later settlement
branches not reached). Post-fix 11 passed, 0 failed/skipped. Three current outcomes: succeeded,
running_or_unknown, ordinary failure. Two older response outcomes while newer query pending.
Six stale outcomes across case/run/task changes. One query yields one request; two explicit
queries yield two; pending held over an event-loop turn without automatic dispatch. Unknown
remains the raw returned status, not reinterpreted as execution. No real elapsed-time test.

Developer only; no independent acceptance. No browser/HTTP/task execution verified; no build or
whole-suite run for this one standalone HTML text update. Existing editVersion guard can suppress
responses if draft input changes; this slice does not redesign that lifecycle or promise a timeout.
Backend startup and archive tests remain paused due to seed import isolation. No merge/deployment.

## Follow-up: final-response ordering and draft edits
Base fa9e118230a8f40dbd3a702926004d1122601878. Four new synthetic cases:
newer finishes first then older success/failure; actual rendered textarea oninput while waiting,
then query success/failure. Fixture gained only synthetic element creation/input events; same
forbidden fetch and in-memory json seam, no image decode or application imports.
Before fix: 13 passed, 2 failed at the draft-edit waiting notice; response-order cases passed.
After fix: 15 passed, 0 failed/skipped using the same single-file command above. Not cumulative.
A pending-query marker updates only feedback, is scoped to the latest query generation, resets
on context change/settlement, and turns waiting into an explicit non-applied-result notice when
input changes. Dirty/current DOM text remain, result is ignored by existing editVersion guard.
No request cancellation, dispatch, retry, polling, task-state or permissions changes. This supersedes
the earlier documented editVersion feedback limitation for these tested textarea paths; not a full
lifecycle or browser guarantee. Other input types sharing the handler not separately exercised.

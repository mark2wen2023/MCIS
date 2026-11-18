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

# W15 response-completion diagnostic (not original acceptance)

The prior exact-runner trace passed default page load and the 503/no-store
header check, then stopped while reading the response JSON. This diagnostic
stamps browser request/response/finished/failed events for the same synthetic
preview POST, and the test host's ASGI send sequence after forwarding the
unchanged messages, including final byte count and SHA-256. It logs no body,
raw headers or URL. It retains default load, the normal Chromium sandbox,
loopback routes, fixed product sources and all assertions, including the
potentially blocking JSON read. It does not consume or replace the response.
Server final send alone does not prove browser receipt.

Follow the prior bounded command: use this checkout's diagnose.py as runner
with the arguments in README, a new evidence directory and an outer 150s
timeout. Retain stdout, stderr, host-first.log, and the actual exit. Correlate
the sole browser preview POST with the sole ASGI sequence; do not send a
second preview during the same run. Treat every result here as diagnostic;
it does not overwrite the original blocked receipt.

## Opt-in user workflow observation (not full acceptance)

Use the original Chrome runner arguments plus --workflow-only. The same single
real preview POST is observed; only the Playwright response JSON read is omitted
for this explicitly scoped run. Status/Cache-Control, requested evidence, actual
error and no result, case isolation, two viewports, three original screenshots,
real server/SQLite reopen and database equality are not skipped. If these pass,
receipt.json reports workflowVerified=true, bodyVerified=false, browserVerified=false
and passed=false (not full gate). A timeout or assertion failure does not pass
this scope. The default run retains every original assertion and the old gate
remains blocked; do not mislabel either run. No mock response or additional POST.

## Case-switch source GET observation (not full acceptance)

This revision only adds observation for the source-list GET after switching
cases. It keeps the original single preview POST, original assertions, normal
sandbox, and --workflow-only to reach the switch without reading the 503 body.
After the first-screen work, the original hash jump to case B is unchanged.
Source GET events are logged without URL, headers or body: synthetic case id,
event, status and failure category. The same-case positive HTTP source-list
GET is recorded from the real request, together with the visible current case
id. If the original hash-switch assertion fails, a separate diagnostic then
drives the user-visible lobby entry and module link (not a direct HTTP stand-in
and not a retry or loosened assertion) and records whether that path differs.
Classify the case-B source GET as never sent, sent then cancelled, returned a
failure, or responded but the UI did not use it. If the association is not
unique, record 未验. This is not a product change and not an acceptance pass.

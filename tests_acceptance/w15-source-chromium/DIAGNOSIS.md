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

## Opt-in native body read (not the original result.json() gate)

Use the original Chrome runner arguments plus --native-body. The same single
real preview POST is used. A page fetch hook, only for this synthetic case,
clones the real loopback POST Response when it returns and reads the clone
with an 8s deadline. The original Response and page behaviour are unchanged.
The run still asserts 503, Cache-Control no-store, and the JSON code from that
clone. It does not call Playwright result.json(), does not issue a second
request, and does not fall back to a host-side body read. If the clone cannot
be read once, the run stops and does not pass. Case isolation, both viewports,
three original screenshots, real server/SQLite reopen and database equality
are not skipped. If these pass, receipt.json reports nativeBodyVerified=true,
bodyVerified=true, browserVerified=true and passed=false (not the original
gate). The default command retains result.json() and its existing 124; do not
relabel either run as a full-package pass.

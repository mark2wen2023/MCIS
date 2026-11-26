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

This revision also observes Chrome CDP Network lifecycle events on the same
page and same single POST: requestWillBeSent, responseReceived, loadingFinished
or loadingFailed. It never reads the body through CDP. encodedBytes is a
browser transport counter, not the JSON body length. Absence of CDP events is
not proof of a network failure, since delivery to the listener can also stall.

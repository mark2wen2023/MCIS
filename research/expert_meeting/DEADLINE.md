# Absolute deadline correction

Parent10ec700. This corrects the protocol, not merely flaky test timing.
For start4194262.256341955, `int(((start+600)-start)*1000)` is599999:
old Meeting.act remained round_open at the specified start+600 deadline.
Deterministic baseline:2 failed/6 passed; original assertions retained.

Define deadline once as start+600 on the injected/default monotonic clock.
A sample `now >= deadline` expires the meeting on that operation. A sample at
the preceding representable instant does not expire early. Quantized elapsedMs
recorded for replay is constrained to the same side of600000, avoiding both
subtraction-rounding late and early transitions. No tolerance or grace period is
introduced. Nonfinite or nonrepresentably increasing deadlines are rejected.

This does NOT remove tick/action dependency: snapshot/export still do not read
time. It does not create a watchdog, hard process timeout or remote cancellation.
Existing integer elapsed event replay stays consistent. Historical snapshots are
still checked for local consistency; an old snapshot cannot prove its wall-clock
accuracy. Real model execution remains0/HOLD; no credentials/network required.

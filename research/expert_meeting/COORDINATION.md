# EXPERTCOORDINATION: cooperative offline boundary

Parent10ec700. Old executor source1d5262c was inspected read-only: _check polls
bridge in its I/O loops; cancel signals an event/adapter and bridge.stop. Its raw
remote constructor remains disabled. It depends on unextracted bridge/engine,
process ownership and transport layers. This candidate imports none of them.
The merged/extracted Meeting.snapshot does not sample the clock: absent tick or
action it can remain stale. No existing frozen implementation is changed here.

Coordination owns a private remote-declared Meeting with one RLock. Every public
control, reserve, settle and receipt boundary refreshes tick before interpreting
state. No background tick is required to observe expiry at those boundaries.
Model/tool attempt limits count nonrefundable reservations:4/8 per turn and16/32
across the meeting, with at most one pending attempt. They are not actual provider
requests, tokens, cost or a proof of usage. Both context and opinions remain under
the existing meeting validation. Attempt IDs are local increasing integers bound
to a ticket, not capabilities or trusted execution authorization.

Stop/expiry changes pending attempts to unknown; late returned declarations cannot
replace unknown. Failed/unknown settlement terminates the meeting; no retry/refund.
Exact duplicate settlement is idempotent, changed settlement rejected. Clock or
protocol failure at either refresh or control/settlement permanently seals the gate, retains last state and records
blockedReason; this stale state must not be displayed as live authorization.
receipt.executionAuthorized/modelExecutionVerified/identityAuthenticated are false.
The meeting may accept an opinion without an attempt record; that remains a pure
protocol declaration and cannot prove execution or satisfy a future real adapter.

Limitations: this is COOPERATIVE, not an autonomous watchdog, hard timeout or
subprocess controller. While no API boundary is called no code runs. No shared
worker integration or atomic permission-to-network-send exists. Calling reserve
then independently sending a request is NOT authorized or protected by this code.
Python private attributes are not an adversarial security boundary. Real runner
integration needs trusted ownership, cancellation acknowledgements/unknown outcomes,
shared atomic admission, deadlines enforced in blocked I/O, and durable provider
usage receipts; none is claimed implemented by this candidate. No automatic
retry, hard process termination, authentication, signed receipt or model execution.
Current real credentials binding unavailable; actual DeepSeek0/HOLD.

Run offline tests with supported service venv:
`PYTHONPATH=. service/.venv/bin/python -m pytest -q research/expert_meeting tests_acceptance/EXPERTRECEIPT`.
Tests use injected clocks and synthetic declarations only, never provider calls.

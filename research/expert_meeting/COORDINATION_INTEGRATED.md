# Combined offline coordination candidate

Base10ec700743e5f958e74bd910066bd28ea3042a34. Exact changed files extracted from
ced79f561821fe274e7916910a37750da76ebc84 (absolute deadline) and
d26314b196c22608bbb57baf933abf5941ebe4a1 (cooperative gate r1). Only append-only
REQUESTS/ROADMAP portions were combined; no source history/preview stack imported.
Both source freeze sets still match. Original red test evidence and assertions
are retained. The old coordination freeze is historical/pre-r1, explicitly
superseded by its r1 freeze; initial failures remain evidence, not current results.

This candidate actually includes the deadline dependency, superseding the earlier
standalone coordination report's missing-dependency HOLD for that specific defect.
It does not lift real execution HOLD. No live model, credentials, browser, network
adapter, process kill or deployment is involved. Gate is cooperative; private
Meeting can be accessed by Python callers and is not an adversarial sandbox.
Without a public operation no watchdog runs. It does not atomically authorize a
send, certify provider usage or enforce hard cancellation on an external worker.

139 combined tests pass, including4 new actual gate+fractional-clock deadline
boundary cases. Second clock-sampling NaN cases (stop, failed, unknown settlement)
were separately rerun:3 pass, same original assertions. The wider count includes
those3; do not add it as separate new coverage. Existing source tests, receipt
checks,21 deadline independent tests and10 coordination independent tests included.
No retries or epsilon were added to make time tests green.

Run from root with supported service venv and PYTHONPATH=., using pytest
--import-mode=importlib on research/expert_meeting plus tests_acceptance/
EXPERTRECEIPT, EXPERTDEADLINE, EXPERTCOORDINATION, EXPERTCOORDINTEGRATED.

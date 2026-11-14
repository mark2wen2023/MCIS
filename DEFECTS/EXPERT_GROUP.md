# Public two-role Pi research independent review

2026-11-14: Independent20/20 tests passed, zero skips; frozen12/12 matched.
No remaining blocking defect found within the frozen research slice.

## EG-D01 — completion receipt failure retained success status (fixed)
Pre-freeze offline reproduction returned status=completed_unverified,
outcome=failed,errorCode=receipt_write_failed after the group_completed callback
raised. The exception path now forces status=not_accepted. Independent regression
executes real Pi fixture loops and injects the final receipt failure.

## EG-D02 — HTTP timeout restarted after headers (fixed)
The former transport computed its read deadline after request/header latency.
The outer asyncio deadline now covers the complete asynchronous request, with
cancellation/cleanup. Independent delayed-header test confirms bounded rejection.

## EG-D03 — child backpressure could bypass deadline (fixed)
The former blocking pipe write could stall without budget checks. Nonblocking
write readiness, short-write handling, bounds and repeated checks now cover it.
The implementer's real nonreading-child regression passes; review confirms the fix.

## EG-D04 — incomplete artifacts ambiguous after late export failure (fixed)
Result JSON now explicitly requires completion-manifest validation. Local verifier
binds result/HTML/receipt hashes and receipt terminal state. Independent final-receipt
and marker faults reject, as do tampering and symlink substitutions. This certifies
local consistency only, never identity, origin or model accuracy.

Remaining gates: no real-model capability acceptance, no native browser acceptance,
no new source-PDF verification and no production identity integration. Explicit
fixtures must not be presented as real provider or human-expert results.

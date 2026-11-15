# Offline worker lifecycle / shared attempt budget candidate

This is an isolated declaration state machine, NOT a trusted worker or execution
permit. No subprocess, signal, network, credential, clock or provider operation.
Input events are synthetic caller claims; executionVerified/ownershipVerified/
dispatchAuthorized remain false. No hard cancellation, no automatic retry/resume.

Fresh exclusive recording file, one owner instance, one pending UUID attempt;
existing files refused and never cleaned up automatically. The existing Ledger
commits reservation before a simulated ticket can return. Four role IDs, two
rounds, per-role/round2 and meeting16 limits are shared across this instance.
Round2 retains Ledger's necessary first-round received check; this is NOT proof
that four experts completed valid independent opinions. No cross-meeting quota.

Required declaration order: reserved → started → result_received → exit_zero →
cleanup_observed. Only the last boundary settles received_unverified. It does
not validate opinion content or model identity. There is no adapter to FourChair,
Pi, old Bridge or product APIs. Wrong-attempt input cannot settle the active one.
Unexpected current-attempt events (including lost ownership/failed exit) stop,
record pending unknown and forbid late acceptance. Operator stop is idempotent;
no refunds. Database exceptions block the instance without retry; commit outcome
cannot be inferred from the exception. A reservation rejection is conservatively
blocked with unresolved status even if its underlying cause was a known limit.

The lifecycle event list is memory-only and reset on each new attempt; the ledger
persists attempt metadata only. Crash leaves reserved pending; no recovery or
complete event audit is implemented. A caller can forge every synthetic event:
never feed this API into production and infer a trusted worker receipt.

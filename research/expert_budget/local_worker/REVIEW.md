# Local process ledger adapter development record

Base70993cc, independent feat/owned-local-worker-ledger. Prior lifecycle declaration
API remains unchanged. This candidate actually starts a fixed Python worker, never
accepts caller-declared PID/exit as an observation. Existing Pi Executor was inspected
read-only at498f807: runner pin, Pi1.5.2 dependency, Bridge tickets, bounded pipes,
remote/raw-key refusal and owned cleanup remain dependencies of future Pi integration.
They were NOT replaced by this Python fixture or claimed available on main.

Ownership module copied unchanged from
498f80756d6d6c3c3f99ec2e14a859629aa76ff9:research/expert_executor/ownership.py.
Byte equality verified before freezing. Original exclusive-reaper/host assumptions
and cleanup limits remain. No historical security tests rerun. Normal initialization
uses its required support check; no security configuration changes.

Developer command:
PYTHONPATH=. service/.venv/bin/pytest -q research/expert_budget research/expert_meeting tests_acceptance/EXPERTRECEIPT
159 passed in1.69s, including9 new tests (not159+9). Six-test intermediate run
passed in0.41s before three additional cases. No skipped tests in selected group.
New tests: real fixed child PID/exit/reap, failed exit, timeout, operator stop,
concurrent refusal, reservation rollback before spawn, settlement rollback after
reap, injected lost acknowledgement after actual commit, injected lost cleanup
receipt after actual reap, shared role budget. Parameterization gives9 cases.
Fault injections are synthetic, while child launch/exit/reap are real local OS
operations; no Pi/LLM/network dispatch. All databases are temporary synthetic files.
Cleanup uncertainty injection reaps first to avoid leaving an actual orphan; it does
not test malicious reapers, actual ownership theft, unreapable kernel tasks or OS
crash. Those unsupported scenarios cannot be inferred passed. No browser/production
or independent acceptance. Ledger semantics described in the contract remain limited.

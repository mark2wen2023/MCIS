# Durable observations connected to the existing offline controller

Base c1597bcf60664e44fa55a36a0b25a12abee41135; branch feat/expert-durable-coordination.
Current main checked94d5e38. This adds an actual wrapper around main's Coordination,
not an independent pretend model executor. No old state machine/controller change and
no integration of the unmerged remote runtime, raw-key or managed-binding branches.

## Dependency decision

Rechecked exact remote heads: execution-intent4b093336, raw-key HOLD498f8075,
managed-proxycafffbd1, owned-process fix6f8f4291 unchanged from the prior inventory.
Full inventory remains README.md. Read-only source inspection confirms main Coordination
owns a private two-role Meeting and tracks model/tool attempts only in memory. Pi
Bridge/Executor is on a different unmerged stack; execution authorization, actual
managed bootstrap and durable dispatch reconciliation are not available on main.
No safety tests/process supervisors/credentials from those branches were rerun.

The four-role ledger v1 has regulations/navigation/investigation/vessel and2 attempts
per role/round, whereas main uses source_attribution/uncertainty_boundary and4 model,
8 tool per turn,16/32 total. Mapping these roles or counters silently would misrepresent
coverage. Therefore this slice binds durability to the REAL existing two-role controller
and leaves four-role ledger/profile unchanged, unconnected. No four-expert run is claimed.

## Implementation

`DurableCoordination(path, clock=...)` owns a fresh Coordination and one SQLite record.
Methods action/reserve/settle delegate to that controller under one wrapper lock, then
commit a metadata observation before returning. No network/process or credential
module is imported. It works with existing synthetic provider-protocol declarations,
not actual Pi/DeepSeek calls. All execution/identity/hard-cancel flags remain false.

Metadata stores schema/meeting ID/phase/state digest/attempt ticket,kind,outcome and
blocked reason. Opinions, quotes, prompts, participant names, credentials and provider
bodies are not written to the database. The observation chain is local consistency,
not an authenticated receipt; exact identical polling writes no new row. New profile
caps observations256 and stops on exhaustion. No token, monetary or cross-meeting quota.

SQLite BEGIN IMMEDIATE makes fresh controller creation exclusive. A nonempty recording
is never resumed or attached by a second controller, even after process exit or normal
completion. Foreign table sets are refused. It is a fail-closed recovery boundary,
NOT a lease/reaper/resume implementation. A new file/meeting does not acquire approval
or a new global spending allowance; a future trusted service must govern this.

A reserved attempt is returned only after its checkpoint commits and it is still active
at the checkpoint deadline check. If the deadline expires between reservation and
checkpoint, the unknown terminal state is saved and no active reservation is returned.
For action, return the latest observed state, not a stale pre-checkpoint ticket.
Existing tool/model limits, pending submission refusal and old snapshots are unchanged.

Any protocol/storage exception blocks this wrapper permanently and cooperatively stops
its gate in memory. It does not retry writes after uncertain commit. Last disk state
may be stale; receipt reports unknown_or_stale rather than a successful durable state.
If ordinary stop/deadline is successfully checkpointed, pending attempts become unknown
on disk. Stop does not kill Pi/provider processes or cancel HTTP. Clock failure also
keeps the original gate blocked; pending declarations become unknown. Invalid operations
are fatal in this new wrapper (stricter than some recoverable base GateError cases).

`inspect_recording(path)` opens SQLite read-only, checks bounded sequence/digest chain,
and exposes metadata only; resumeAllowed/executionAuthorized/authenticityVerified are
false and currentRuntimeStateKnown=false. It neither reconstructs the meeting nor
certifies current execution state. A forged/rehashed local DB is not authenticated.
No dispatch permit or provider proof can be inferred from a stored reservation.

## Actual developer tests

```
PYTHONPATH=. service/.venv/bin/pytest -q research/expert_budget research/expert_meeting tests_acceptance/EXPERTRECEIPT
```
122 passed in0.86s. Includes first10 new controller cases,11 parent ledger tests and
existing meeting/receipt regression. Subsequently added failure/unknown settlement
cases and ran the whole controller file:
```
PYTHONPATH=. service/.venv/bin/pytest -q research/expert_budget/test_controller.py
```
12 passed in0.21s. Do not sum122 and12 as unique/full-system coverage. Runtime code
unchanged after122; final additions are tests only. Initial controller7 tests also passed.

New tests cover real wrapper→Coordination→Meeting transitions, complete two-role/two-
round synthetic review with model/tool attempt declarations, persisted reservations,
two competing constructors, pending-stop/deadline unknown, per-turn limits, SQL trigger
failure before insert and permanent refusal after recovery, late deadline before return,
clock failure, unchanged polls, observation budget, failed/unknown settlement and no
retry. Socket/Popen forbidden in an ordinary test; generated opinion text verified
absent from SQLite metadata. No network requests, Pi/DeepSeek, provider usage, browser,
SSO or independent acceptance occurred. No restricted historical/security/ECFC probes.

## Next prerequisites still HOLD

A reviewed four-role meeting/prompt/tools contract and compatible persistent attempt
policy; trusted source disclosure and execution authorization; actual managed credential
bootstrap and worker binding; atomic durable dispatch ownership/reconciliation; owned
process/HTTP cancellation and late-result handling; verified real request/response
receipts, token/money controls and privacy boundaries. This wrapper cannot be installed
as a real executor merely by passing a boolean or by replaying its recording. No service
API, case writer, deployment or automatic task recovery is introduced. No push/merge.

# Four-expert durable reservation prerequisite — offline candidate

Base/current remote main checked:94d5e38c926fda232bb987b60fa9145e4bcf01a7.
Branch research/expert-execution-readiness. This adds a separate SQLite reservation
experiment, not a model execution gate, production API or enabled expert meeting.
No network requests, Pi processes, secret/env reads, private cases, software installation,
platform settings changes, real-model testing or previously restricted probes.

## Inventory of existing dependencies (read-only)

| Layer / exact inspected source | Existing behavior | Missing / restriction |
| --- | --- | --- |
| main expert_group/packet.py + expert_meeting | Two roles source_attribution / uncertainty_boundary; two rounds/four turns;16 model and32 tool allowances;600s protocol deadline | remote is a declaration with no transport. Model/Pi/identity flags false. Not four maritime experts. |
| design22537b182c9e6db90e925ac664b6e34c26458671 | Approved business proposal: regulations, navigation, investigation, vessel; manual start, frozen source, human decisions | Design is not execution authorization; source/version, interventions and outcomes need separate contracts. |
| Pi bridge0a4bf2224fc29afe08df9231aa0aad23dffca72f | Fixed packet/tools, ticket/context binding, previous complete round sharing,4/8 per-turn16/32 total protocol counters | Initially scripted only. No persistent reservation, authenticated execution or actual request cost. |
| executor3125eaf4745cf4b2f83944a56a049823c032f436; ownership6f8f4291d97e1c1be47676b11cd819f6c36ef46a | Fixed pinned Node runner; Pi package versions1.5.2; bounded stdio, process groups, exclusive reaper/waitid ownership,120/600s checks | Prior documented tests distinguish actual Pi/scripted provider from real DeepSeek. POSIX ownership assumptions and kernel limits remain. These tests/processes were NOT rerun this turn. |
| remote8f2fa052a1f9cbf28446de1278fbfdd161915fd0 | Fixed DeepSeek endpoint/model string in transport; isolated provider worker/bridge receipt mechanisms | Earlier raw-key paths are not authority to run now; model identifier is a code declaration, not currently verified provider availability. |
| managed proxy cafffbd1dcc157be8e87b0187c7aecc5639eee22 | Fail-closed proposed managed-binding validation, explicit TLS/proxy policy, no env fallback | Trusted platform bootstrap/worker binding unavailable. Normalized schema is not an actual platform API. Do not replace it with caller ready flags, arbitrary proxy or fake SSO. |
| raw-key hold498f80756d6d6c3c3f99ec2e14a859629aa76ff9 | Raw-key live transport/worker/executor/old CLI deliberately blocked; explicit synthetic MockTransport only | Hold must be retained in any integration. No rerun of its security/credential tests this turn. |
| intent4b093336b63545e40bd9fddbb8297a0953333c4e | Offline intent export and always-blocked preflight; UUID/pinned public packet | No authenticated service authorization, durable pre-dispatch ledger or authorized hard cancellation. This turn does not duplicate/remove intent hold. |

These remote candidate heads were checked using normal git ls-remote; missing local
intent/hold refs were fetched read-only. No branch was merged/cherry-picked. Source
files and docs were inspected; prior reported model, process, browser or safety tests
are not new verification. Main worktree lacks .agents/skills. AGENTS/HANDOFF were read.
The old tools/pi-transcript bridge seen in an older local checkout is NOT present in
this exact main; do not infer it is the current main expert execution path.

## Selected actual gap and implementation

Candidate remote adapter budgets are in-memory and explicitly forbid resuming after
crash. New ledger.py persists reservation identity/count/outcome before returning from
SQLite COMMIT, serializes independent connections with BEGIN IMMEDIATE, and retains
unknown/pending reservations across reopen. It stores only pinned public packet SHA,
UUIDs, role/round/ordinal/outcome, no prompts, opinions, URLs, keys or endpoint overrides.
Foreign existing databases and incompatible ledger versions are refused.

Four-role IDs follow the existing maritime proposal. New independent profile
mcis.public-four-expert-reservations.v1 fixes two rounds, two model-attempt reservations
per role per round, total16. This fits the old total16 without silently doubling it
for four roles. It intentionally differs from old4-per-turn/two-role policy and is NOT
a drop-in bridge replacement. No tool/token/money/time quota is implemented here;
existing tool32 and deadline controls must remain and be jointly redesigned/verified
before integration. Received first-round attempts are only a necessary ledger check,
NOT proof that all roles completed valid opinions or that sharing is authorized.

create is idempotent for the same meeting/public packet and cannot clear stopped state.
reserve refuses any unresolved reservation, changed duplicate binding, wrong round/role
or exceeded limits. Same attempt lookup returns replay=true, never another dispatch
permit. All returns say executionAuthorized=false; this module itself dispatches
nothing. A new meeting ID is NOT a new user authorization: a future trusted service
must bind one approved intent to one ledger meeting and enforce cross-meeting limits.

settle accepts explicit local outcome declarations received_unverified/not_dispatched/
unknown. They are not authenticated provider receipts. Unknown/not-dispatched stop the
meeting and do not refund its attempt. stop persists stopped and converts pending to
unknown; it does not kill a process, cancel HTTP or guarantee the provider did not bill.
Late conflicting settlement is refused. Reopen does not auto-resume pending requests.
No automatic retries. A commit exception must be treated as uncertain by a future
caller; inspect the same attempt ID, never blindly allocate/send a new one. Current
injected SQL failure test proves rollback before commit only, not uncertain commit or
crash/power-loss durability on every filesystem.

## Development verification

```
PYTHONPATH=. service/.venv/bin/pytest -q research/expert_budget research/expert_meeting tests_acceptance/EXPERTRECEIPT
```
112 passed in0.91s. New ledger11 cases cover four roles/two rounds/16 reservations,
reopen with pending, exact replay, concurrent connections, sticky unknown/not-dispatched,
turn/round limits, invalid binding, injected SQLite insertion failure, foreign DB refusal,
no socket/Popen and stopped-state persistence. Earlier ledger+meeting group75 passed
before final foreign-DB/no-network tests. All new cases are constructed SQLite tests;
no genuine model/remote transport/Pi execution or independent acceptance is claimed.
No test data files/databases are committed. Full service/frontend suite not run.

## Runnable scope and next gate

Runnable today: offline Python reservations and existing two-role protocol tests only.
Real four-expert meeting remains HOLD. Required: independently reviewed four-role
meeting/prompt/tool contract; new disclosure digest including shared opinions; trusted
server identity/explicit authorization; actual approved managed credential binding;
atomic reservation-before-dispatch integration; non-replayable dispatch ownership and
persistent reconciliation; owned Pi/provider cancellation with late/unknown result
handling; receipts bound to actual source/config/authorization. No reservation record
or metadata ready flag supplies these guarantees. Model cost/token usage remains
unknown. Human review and original source boundaries remain unchanged; public packet
is a pinned excerpt with three manual test claims, not three independent sources or
verified conclusions. No real case/LLM/browser/production acceptance; no push/merge/deploy.

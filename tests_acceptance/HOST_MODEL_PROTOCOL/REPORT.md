# Host model protocol — developer evidence only

Base: 14ef270107b7a6dc274deac892059dbcd230a014.
Reference-only: Pi bridge 0a4bf2224fc29afe08df9231aa0aad23dffca72f;
owned executor dependency 6f8f4291d97e1c1be47676b11cd819f6c36ef46a.
Neither reference tree has been merged or enabled.

## Scope

HostModelProtocol binds meeting/ticket/role/round/context to RequestBudget. Its
input is exactly `{op: "model", requestId: "<ticket>:model:<ordinal>"}`.
The existing fixed RequestWorker converts REQUEST n to this message and uses the
adapter for reservation and response settlement. A new reservation returns only
after SQLite commit, before the existing stop/deadline check and GRANT. Duplicate
requests never produce another grant. Pending/unknown results are not retried.
The adapter does not accept a transport callback, credentials or an enable flag.
Reservation remains dispatchAuthorized=false: it is not execution authorization.

Each role/round retains two requests; the meeting retains sixteen total. A third
request sets partial_budget_exhausted without adding a reservation. Earlier
responses remain stored; the supervisor retains prior completed fixture roles
and lists every other role as unfinished. Two responses alone do NOT prove an
expert role completed. No new opinion or completion semantics were introduced.

The existing single run lock and ownership module remain the sole process owner.
No new reaper, poll/wait path or process was added. The ownership file is unchanged
and matches the 6f8f429 module blob 5aeb9078196e5a615f4d9bab79672e28d8321f7a.
Stop/deadline/unknown/cleanup code and all existing limits remain unchanged.
The protocol object is intended for the serialized host, not concurrent callers.

## New tests reviewed individually before execution

All use synthetic messages and temporary SQLite, no child process, model, network,
real cases, browser, permission tests or write-refusal probes.

Command (from repository root):

```bash
/workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider \
 research/expert_budget/test_host_protocol_candidate.py::test_reservation_visible_before_simulated_dispatch \
 research/expert_budget/test_host_protocol_candidate.py::test_duplicate_completed_request_has_no_second_grant \
 research/expert_budget/test_host_protocol_candidate.py::test_pending_duplicate_remains_unresolved \
 research/expert_budget/test_host_protocol_candidate.py::test_unknown_blocks_next_dispatch_and_preserves_receipt \
 research/expert_budget/test_host_protocol_candidate.py::test_third_request_preserves_prior_role_and_partial_responses \
 research/expert_budget/test_host_protocol_candidate.py::test_four_roles_have_separate_two_request_allowance
```

Result: **6 passed in 0.13s**, developer run. No other tests run.

## Remaining boundaries / HOLD

This is a host protocol adapter wired to the existing fixed local worker, NOT the
Pi runner or provider. The process integration was inspected, not executed this
round. Existing broader tests were deliberately not run. No independent review.
The unknown test explicitly declares unknown; it is not a crash/commit-failure
experiment. No cross-process recovery, response replay, token/currency budget,
provider cancellation or descendant termination guarantee was added.

Actual Pi remains blocked on missing installed official dependencies and the
unfinished owned Executor/Bridge integration. The old group engine's poll/wait
must not be mixed with exclusive ownership. The owned Executor uses a distinct
Bridge and role/packet contract; that requires a separately reviewed adaptation.
No download attempted, credential inspected, or real model called. Four-seat
real execution remains HOLD; production entry points unchanged.

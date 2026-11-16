# Stable tickets and partial outcomes — pure candidate

Parent: 989c7e1553bf614c6115947a3ac0297c3952eb4b.
No existing host, Bridge, Executor, ownership or production file changed.

## Protocol

`initial(meeting_id)`, `step(state, action)` and `summary(state)` are pure in-memory
functions. Four ordered roles, two rounds. UUID5 binds the protocol version,
meeting UUID, round and role. Context is stored beside the ticket: a changed
context on the same binding rejects rather than issuing a new allowance.
The identifier is NOT a capability, authorization, reading proof or persistence.
This does not map or migrate old two-role Bridge tickets into the four-role model.

Requests use `<ticket>:model:<ordinal>`. Repeated pending, received or unknown IDs
never allocate another reservation. Pending prevents further requests; unknown
halts the meeting. Each turn has at most two requests, the meeting at most sixteen.
Third request gives partial_budget_exhausted and preserves prior turn/request data.
Summary reports each round/role as not_started, active, incomplete_unknown,
incomplete_budget or completed_declared. No response count alone completes a turn;
a separate simulated complete action is required. Even that action proves neither
runner exit nor expert opinion acceptance. All execution/persistence flags false.

Inputs are in-process state from this API, not trusted deserialization of a saved
meeting. Recreating initial state loses prior context and reservations. This is
explicitly NOT restart recovery, a durable budget or an execution gate. Future
wiring must bind the same identities/context to the durable ledger and preserve
Bridge validation and owned-executor completion checks. No provider is attached.
Existing HostModelProtocol remains unchanged and is NOT integrated with this reducer.

## Individually reviewed new ordinary tests

Pure synthetic workflow only: no DB, files, processes, model, network or credentials.
No paused tests, security tests, write-refusal probes or old suites run.

Exact developer command (repository root):

```bash
/workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider \
 research/expert_budget/test_stable_protocol_candidate.py::test_stable_binding_and_changed_context \
 research/expert_budget/test_stable_protocol_candidate.py::test_meeting_and_role_bindings_are_distinct \
 research/expert_budget/test_stable_protocol_candidate.py::test_duplicate_pending_and_received_never_reserve_twice \
 research/expert_budget/test_stable_protocol_candidate.py::test_unknown_keeps_slot_unfinished_and_blocks_new_request \
 research/expert_budget/test_stable_protocol_candidate.py::test_budget_partial_keeps_completed_and_unstarted_separate \
 research/expert_budget/test_stable_protocol_candidate.py::test_two_rounds_sixteen_requests_are_only_declared_complete \
 research/expert_budget/test_stable_protocol_candidate.py::test_pending_response_cannot_be_completed_or_skipped \
 research/expert_budget/test_stable_protocol_candidate.py::test_transitions_and_summaries_do_not_mutate_input
```

Result: **8 passed in 0.04s**, developer synthetic tests, not independent acceptance.
Pi/runtime/real models remain HOLD. No downloads, installation, model calls or
process tests. No production or browser validation; no merge or deployment.

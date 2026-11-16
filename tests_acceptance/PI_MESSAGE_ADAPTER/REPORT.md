# Isolated Pi-shaped message adapter (not a Pi execution)

Parent: 7182e1397ab1b34bdc2cadd1443bd27fb3fa9482.

SimulatedPiMessages -> V2HostProtocol -> revision-3 ledger is the only writer chain.
No old Meeting/Bridge object or v1 writer is used. The adapter does not start or
reap processes and cannot enable a provider. Every output explicitly forbids
dispatch/new grants and denies execution verification.

The host supplies operation IDs. The adapter binds model requests to its stable
issued ticket and sequential request ID, persists the reservation, validates the
supplied synthetic assistant message, and records SHA256 of its canonical JSON
through the result operation. This is not the hash of raw network wire bytes or
proof of a provider response. It never calls complete_declared. Even valid done
would only reach lifecycle_unverified; no exit-observation API exists here.

Validation provenance:
- Reuses expert_group.packet._strict/_packet/_validate and pinned public packet.
- message_validation._assistant is copied unchanged from
  6f8f4291d97e1c1be47676b11cd819f6c36ef46a:research/expert_group/engine.py.
  Only its pure imports are retained, excluding model transport and execution.
- Exact pending tool-call matching, repeated-tool-ID exclusion, read-before-review,
  complete item coverage, exact source quote and 2000-character review-field limit
  follow the old Bridge rules. Wire limits remain 262144 bytes and 8 tools/turn.

Scope/remaining gaps:
- Single first-round turn only. Fresh ledger chair ordering means the first role
  regulations is the usable start. No four-seat iteration, role prompts, prior-round
  opinion transfer, full old Bridge replacement or lifecycle acceptance.
- Tool state/candidates/messages are memory-only. Supplied operation_id for tool/done
  messages is NOT a durable ledger operation; only issue/model/result are persisted
  here. No tool transcript/crash-recovery claim. This must be solved before any
  full meeting integration; no second ledger is introduced as a workaround.
- Existing two-call quota stays. The sample read_packet + validate_review flow
  consumes two model responses; requesting a third to obtain final completion
  stops with budget_exhausted. Candidate review is not a completed role.
- No transport deadline/process ownership proof is provided by this message-only
  adapter. Existing owned Executor is not connected and has not been changed.
- No install/download, credential reads, real Pi, model, process or browser runs.
  Public packet source strings are used only in synthetic review fixtures, not
  evaluated by a real model. Real execution HOLD. No merge/deployment.

## Individually reviewed new ordinary tests

Only the following five new nodes ran. Synthetic assistant/tool messages and
 temporary SQLite; no paused/write-refusal/security suites or old tests executed.

```bash
/workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider \
 research/expert_budget/test_pi_message_candidate.py::test_model_request_and_response_digest_bind_to_ledger \
 research/expert_budget/test_pi_message_candidate.py::test_read_packet_tool_uses_fixed_source_and_context \
 research/expert_budget/test_pi_message_candidate.py::test_review_tool_keeps_unverified_candidate_and_third_request_stops \
 research/expert_budget/test_pi_message_candidate.py::test_mismatched_tool_message_blocks_without_completion \
 research/expert_budget/test_pi_message_candidate.py::test_response_digest_never_accepts_done_by_itself
```

Result: **5 passed in 0.10s**, developer synthetic only. Independent review pending.
Static text comparison also confirmed copied _assistant function equals pinned source.

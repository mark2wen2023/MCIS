# Stable binding to durable request ledger — isolated developer candidate

Parent: 797a588ed16b95630eb66f11311831814f09bc71.

## Actual chain

DurableHost -> stable_protocol._ticket (same deterministic UUID mapping) ->
HostModelProtocol -> RequestBudget SQLite transaction. No new request counter or
pure reducer request-state copy is used. SQLite is the source for ticket bindings,
request outcomes, receipt digests and remaining allowance. The host keeps only
turn order/completion declarations and its stopped flag in memory.

A new ledger file is required; no reopen/resume interface. Issue binds the stable
UUID/context before publishing the ticket to the caller. Request returns
fixtureGrantReady=true only after RequestBudget.reserve committed. That marker is
NOT execution authorization: dispatchAuthorized and executionVerified stay false.
No transport callback or worker is connected. A future owned fixture host must
still check stop/deadline/ownership immediately before grant.

Duplicate requests stop this host without another reservation; the ledger is
conservatively stopped_unknown while existing received receipts remain unchanged.
Explicit unknown persists through the existing stop method and blocks all later
requests. Budget exhaustion preserves partial_budget_exhausted (not overwritten by
stop), earlier completed_declared turns, the incomplete_budget turn, and unstarted
seats. Two per turn, sixteen total remain enforced by RequestBudget.

Exceptions in binding/reservation/settlement mark this host blocked and
consistencyUnresolved; this means consistency has not been established, NOT that
an actual uncertain SQLite commit was reproduced. No subsequent compensating
writes/retries are attempted on that path. Completion checks the ledger responses,
but is still only a simulated declaration, not a process/provider acceptance.

## Limitations

Serialized single host only; no concurrent callers or external ledger mutations
are supported or tested. No durable turn progress/opinions, crash recovery,
provider dispatch, real Pi, identity authorization, model calls or process tests.
Pure-protocol mapping and HostModelProtocol are reused; existing implementations,
process ownership code and production paths are unchanged. Actual unknown commit
and crash behavior were NOT tested. Explicit unknown is a synthetic input.
The existing public packet binding is retained; no real report/model is evaluated.
Real execution remains HOLD. No merge/deployment.

## Individually reviewed new ordinary tests

All new tests contain temporary synthetic SQLite data and simulated host messages;
no security/write-refusal probes, paused tests, browser or subprocess calls.
Exact command from repository root:

```bash
/workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider \
 research/expert_budget/test_durable_host_candidate.py::test_stable_binding_persisted_once \
 research/expert_budget/test_durable_host_candidate.py::test_durable_reservation_precedes_fixture_ready \
 research/expert_budget/test_durable_host_candidate.py::test_duplicate_stops_without_second_reservation \
 research/expert_budget/test_durable_host_candidate.py::test_unknown_is_durable_and_later_seats_not_started \
 research/expert_budget/test_durable_host_candidate.py::test_third_request_keeps_prior_declared_completion \
 research/expert_budget/test_durable_host_candidate.py::test_four_seats_two_rounds_sixteen_persisted_requests
```

Result: **6 passed in 0.21s**, developer synthetic tests only. No other tests run.
Independent review pending. No credential reads, installation or download.

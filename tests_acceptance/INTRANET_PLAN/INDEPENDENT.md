# Independent acceptance: intranet metadata and query intent

Reviewed against baseline `254167e3e957784fd9d2d136a275731f33314d9b` and
`contracts/intranet-plan.md`; isolated Python implementation and CLI only.

Command (2026-11-14):

```
service/.venv/bin/pytest -q -p no:cacheprovider tests_acceptance/INTRANET_PLAN/test_independent.py
```

Result: **35 passed, 0 skipped**, 0.21 seconds. Tests written by independent reviewer;
implementation was not changed by reviewer. All input identifiers/reference names are
synthetic test fixtures, not actual accounts, endpoints, vessels or case data.

Covered:

- All four source categories and API/MCP transport labels, unconfigured/unchecked states.
- Exact case/vessel preservation, timezone normalization, missing input pending fields.
- Exact time-window boundary and one microsecond over, invalid/equal/reversed times.
- IMO checksum, zero MMSI, duplicate source/vessel, source capacity and strict integer bounds.
- Secret and unknown fields rejected without echo; URL, command, nested and wrong-type references rejected.
- Socket construction and DNS resolution replaced with failure traps for in-process plan generation;
  no network call occurred. Input unchanged after planning; all plans nonexecutable.
- Real local CLI subprocess tests for duplicate JSON keys, malformed JSON, nonfinite value,
  invalid UTF-8, excessive nesting and oversized input: exit 4, fixed JSON error, empty stderr.

No blocking defect found within this bounded offline contract. This verifies local
validation/planning only, not external connectivity, account validity, real vessel
identity, data collection, model capability, HTTP authentication or browser integration.
No intranet probe, real API/MCP request, database mutation, deployment or merge was performed.

Integration gap remains explicit: no production UI/HTTP/DB configuration persistence;
future authorized adapters must resolve references and enforce case access independently.
Reference syntax is not a secret classifier: an operator intentionally putting a secret
in an otherwise valid identifier cannot be detected reliably. Contract explicitly forbids
that misuse and accepts references only; no raw credential field is supported.

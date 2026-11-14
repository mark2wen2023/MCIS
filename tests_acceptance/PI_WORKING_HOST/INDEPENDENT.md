# Independent Pi working-host review

Scope: `pi_working_host.py`, private shared `_save_checked` transaction refactor,
and callers in working history. Independent native subtask, not separate Codex
application execution. No external provider request or credential read; all
model responses are mocked. Actual SQLite and trusted-host state are exercised.

## Result

No blocking issue found in this narrow backend-only slice. The caller supplies
only an operation ID to save; candidate, evidence and trace are retained by the
trusted host, not accepted from the save caller. Stored result is re-parsed and
exact citations/source/policy bindings are rechecked in the same write transaction
as existing current-session, case and dedicated working-write authorization.
Remote provider identity remains declared, not attested; no approved facts.

Independent tests in `service/tests/test_pi_working_independent.py` cover:
- Mutated returned proposals/citations/provider labels and mutated save response
  cannot alter host-owned accepted output or stored data.
- Same-operation retry returns one existing row; another run using that operation
  is rejected, not mistaken for a replay.
- Revoked write permission/session and changed source deny save/replay/read.
- Final transaction recheck failure rolls back the inserted row.
- Unvalidated terminal output closes the run and cannot be saved.
- Closed host cannot dispatch or retry saving.
- An approval digest for one session cannot authorize another session.
- Existing supplemental archive rejects Pi format rather than silently omitting
  it. A case containing Pi proposals cannot currently use that old export path.

Combined command:
`PYTHONPATH=pi-transcript/service mcis-work/service/.venv/bin/pytest -q pi-transcript/service/tests/test_pi_working_host.py pi-transcript/service/tests/test_pi_working_independent.py`

Result: **15/15 passed, zero skipped, 61.84s** (5 primary + 10 independent).
One existing Starlette TestClient deprecation warning. Counts overlap primary
results; do not add them as new unique tests to broader regressions.

Not verified: real LLM in this review, actual Pi process-to-durable-save transport,
production UI/HTTP mounting or login, complete archive support, CI, deployment.
Python final terminal==validated exact-string condition was not changed; a
Node structural-equivalence unit pass does not prove remote end-to-end acceptance
when model final bytes differ from the validated string.

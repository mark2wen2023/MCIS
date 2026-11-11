# HTTP core error redaction verification — 2026-11-12

Base: b667bf480f67efb32d31ec5911b1e1935e564281. This is a narrow error-presentation hardening, NOT closure of the raw align path-reading or authentication risks.

## Implementation and compatibility

`colreg.router._core` now maps known CoreError codes to fixed HTTP status/message and maps unknown codes to CORE_ERROR/502. No core stderr, command path, arbitrary envelope code/message is returned through this catch block. Successful responses and direct CLI behavior are unchanged. No database, source-report, network/security setting, listener or role change. Contracts and REQUESTS record the error-message compatibility change.

## Evidence

142 service/contracts source files were reconstructed and Git blob-verified against the exact base before changes (131 identical files reused by verified bytes; 11 fetched from pinned head). This is a PARTIAL source snapshot, not a clone or full product verification. No old database or core executable was reused. Installed Python dependencies alone were reused.

Initial red test: 10 failed / 2 passed against unmodified router; sensitive strings are synthetic. Implementation tests: 17 passed. Independent review added 12 tests, including real core_client with mocked subprocess failures, malformed envelopes, and CPA success. Final checked-in acceptance location rerun: **29 passed**, 1 Starlette/httpx deprecation warning, 1.62s. No .NET, seeded app, browser or complete service regression is claimed for this slice. Run from repo root with `PYTHONPATH=service service/.venv/bin/python -m pytest tests_acceptance/HTTP_CORE_ERRORS -q`.

## Remaining risks / deliberately not changed

- Old raw `/core/align` still accepts local paths and lacks case authorization; only response-error disclosure is narrowed. Disabling/restricting it changes the documented and tested API and remains a separate proposal.
- Client-declared roles/operators remain single-user demo context, not authentication.
- Malformed core envelopes can still raise non-CoreError exceptions and return generic HTTP 500 under non-debug FastAPI. This slice does not catch all Exceptions or claim all errors are robustly normalized.
- Direct CLI diagnostic messages and successful/raw align payloads are outside this redaction scope.
- No merge or deployment. Existing canonical-source historical database remediation remains untouched.

# Independent issue archive trial HTTP review

Scope: explicit isolated ASGI trial transport for supplemental issue bundle export/import/list/read. Not production authentication, browser integration, deployment, full-case restore, or `.mcase` replacement. Historical payloads remain inert and untrusted.

Final verification: **36 passed, zero skipped, 18.41 seconds** (20 independent + 16 main). One existing Starlette/httpx deprecation warning. Command:

`PYTHONPATH=issue-journal/service mcis-work/service/.venv/bin/pytest -q issue-journal/service/tests/test_issue_archive_http.py issue-journal/service/tests/test_issue_archive_http_independent.py --disable-warnings`

Independent tests verify authorization before receiving bytes, duplicate auth/type/length and spoofed operator/transfer headers, actual multi-chunk 8 MiB boundary with no third read, declared length mismatch, grant revocation during body receive, disconnect and cancellation before service invocation, sanitized injected timeout, committed-result response failure and same-bundle digest retry without duplication, HEAD without materialization, raw canonical export bytes and fixed ASCII attachment/no-store/nosniff headers, case-name namespace collision regression, default protected app unmounted, and no implicit archive-table initialization.

Main tests verify round-trip export/import/read/list and replay, raw bundle rejection, revoked write grant still allowing export, session revocation, exact route/method/query restrictions and rejected transport headers.

An initial independent run had missing imported `ready` pytest fixture (19 setup errors; main 16 passed), fixed in test imports before final run. This was a test setup error, not product failure. No product defect was found within this scope.

Cancellation guarantees are limited: body-receive cancellation performs no restore; after synchronous restore starts, a lost connection/result can follow commit. The tested recovery is retrying the same bundle digest, not asserting rollback of committed data. Timeout is injected, not a real 30-second network stress test. No actual sockets, reverse proxy, IdP, browser CORS login, or adversarial host was tested. ASGI trusted host creates the app and supplies database/settings; no auto-provisioned accounts/grants.

Reviewed SHA256:
- `archive_http_trial.py`: `d810653110c7ea1e6c91eb3953362e6793dd6899a9a7690d32b119819b4a84f5`
- `identity/http_trial.py`: `d237f560f5faa8d86275ff7a274e19b1f106c56c3ed3bed7b6ae10bb004a0780`

Independent tests frozen. No remaining blocker within reviewed scope. Reviewer did not edit product code, push, merge, or deploy.

# Authenticated HTTP integration trial

Base ed090af304edd03ad0aa5a2f64152b8eb1196b44. Explicit test-only app,
no CLI/default app activation, no old route mounting, no deployment/merge.

Final local command: MCIS_PREFLIGHT_REAL_CORE=/tmp/mcis-preflight-core.sh
service/.venv/bin/pytest -q service/tests/test_identity_http_trial.py
service/tests/test_identity_http_trial_independent.py service/tests/test_local_authority.py
service/tests/test_local_authority_independent.py service/tests/test_internal_unreviewed_save.py
service/tests/test_internal_unreviewed_save_independent.py service/tests/test_protected_app_closed.py
service/tests/test_protected_app_independent.py service/tests/test_unreviewed_api_closed.py
service/tests/test_unreviewed_api_closed_independent.py

307 passed, zero skipped, 79.88s (one Starlette/httpx deprecation warning).
17 new primary HTTP tests and20 new independent tests plus prior270 (counts overlap
with separate runs). Actual W2 exercised in one new authenticated HTTP TestClient
path and one existing internal save test. Other fault/race fixtures use controlled
core output. This is ASGI/TestClient, not a socket/browser/real IdP/LLM test.

Independent review verifies raw-ASGI chunk limits, duplicate headers, pre-body
identity denial, concrete legacy-path isolation, revocation during body receive,
timeout/disconnect, non-leaking unknown errors, fake-role/operator immunity.
Code review prompted checking chunk budget BEFORE copying into accumulation buffer.
No credentials/default users are published or seeded. Sessions remain local DB
capabilities from explicit trusted provisioning. Existing old app remains unsafe
for exposed authenticated service; this trial unmounts it rather than migrates it.

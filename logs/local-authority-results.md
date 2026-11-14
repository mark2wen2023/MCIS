# Local identity authority acceptance

Recovered draft base: 6248b88246fb980f0332e71cf562f5fd18aeee6b.
Three modified pre-existing implementation files compared with fetched remote base,
all match the predecessor snapshot before this patch. No old REQUESTS/ROADMAP copy
will overwrite remote content. Closed-entry interrupted draft preserved unchanged.

Final local command:
MCIS_PREFLIGHT_REAL_CORE=/tmp/mcis-preflight-core.sh service/.venv/bin/pytest -q \
 service/tests/test_local_authority.py service/tests/test_local_authority_independent.py \
 service/tests/test_internal_unreviewed_save.py service/tests/test_internal_unreviewed_save_independent.py \
 service/tests/test_protected_app_closed.py service/tests/test_protected_app_independent.py \
 service/tests/test_unreviewed_api_closed.py service/tests/test_unreviewed_api_closed_independent.py

270 passed, zero skipped, 46.06s (one Starlette/httpx deprecation warning).
Includes 28 primary identity tests, 13 independent identity tests and existing
internal-save/closed-entry regression. Existing independent save uses one actual
W2 invocation; new identity fault/race cases use explicit controlled core output.
These are local SQLite/API/ASGI tests, not CI/browser/live LLM or production login.

Independent review found an externally preopened deferred BEGIN was not proof of
reserved writer ownership. Fixed with exact transaction/connection/thread proof
and reverified. Initial archive export failed unknown-table completeness guard;
three deployment-local authority tables now explicitly excluded, not serialized.
Actual archive export/empty restore leaves all three empty. No HTTP route enabled,
no legacy role-header trust added, no merge/deployment.

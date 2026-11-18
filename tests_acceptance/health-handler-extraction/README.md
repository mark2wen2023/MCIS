# Health handler extraction — developer checks, pending independent review

Base: 6d5069b9d320dcaddab28b95f8ed265bfc567b67.
Independent candidate; not integrated into UI/main or a runnable minimal package.

Product change: move the existing zero-argument health function to mcis_service/health.py.
Its sole import is the existing code-only package version constant. Existing create_app
registers it using app.get("/api/v1/health", tags=["meta"])(health), the same decorator
application, method, path, function name and unannotated return contract:
status=ok, service=mcis-service, version=__version__. No new factory or configuration.

Health means liveness only. It does not certify DB, source integrity, business readiness,
authorization, archive recovery, or safe startup. Existing create_app still initializes
DB and broad routes; this extraction does not authorize running it.

Validation (three selected nodes passed):
python -B tests_acceptance/health-handler-extraction/check.py HealthContract.test_actual_handler_contract HealthContract.test_response_is_fresh_and_not_readiness HealthContract.test_main_registration_ast_only

Checker reads only health.py, code-only __init__.py and main.py source.
It compares health AST to a fixed no-I/O shape, obtains the literal version without
package import, executes the actual reviewed handler with a custom version-only importer,
and checks fresh responses. Main is parsed as AST only; registration is structurally checked.
No FastAPI/HTTP test, real package import, backend, DB, seed, model, real materials,
permissions/refusal probes or paused tests. This is not full import-closure or HTTP acceptance.

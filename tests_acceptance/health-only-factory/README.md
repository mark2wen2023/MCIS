# Health-only factory — review candidate, NOT startup approval

Base 064341a0fc19b8426127b096ef8f29a1eb8ec714.
New module service/mcis_service/health_app.py only. Standard main/__main__/configuration
remain unchanged. No CLI, module-level instance, server command or auto-run entry.
create_health_app imports FastAPI and the exact existing health function, registers
GET /api/v1/health with tags=["meta"], and disables docs_url, redoc_url, openapi_url and
swagger_ui_oauth2_redirect_url. Response indicates liveness, NOT business readiness.

Intended MCIS source closure: __init__.py (literal version), health.py, health_app.py.
No DB, seed, business router or environment-configuration dependency in those modules.
This is a static source observation, not proof about installed FastAPI or Python runtime.

Three selected developer checks passed:
python -B tests_acceptance/health-only-factory/check.py FactoryContract.test_definition_does_not_construct_app FactoryContract.test_only_expected_route_and_docs_disabled FactoryContract.test_each_call_has_separate_collector

Tests read exactly the three files above, validate AST shape before executing reviewed
source with in-memory import substitutes. FastAPI is never imported: an entirely handmade
route collector records constructor options, route method/path and handler identity.
Actual health source is executed with a version-only substitute, no package import.
Checks cover no construction at definition, disabled-document arguments, one registration,
same handler and separate collectors. They do NOT inspect FastAPI-generated routes,
OpenAPI behavior, framework middleware, HTTP or actual lifecycle.
No main import, service startup, DB, material reads, model, permission/refusal or paused test.

## Still required before packaging / real execution
- Independent review of new module and exact source hashes.
- Pin Python binary/stdlib/native runtime and actual FastAPI/Starlette/Pydantic/transitive
  artifacts, versions, provenance and full payload hashes; current lower-bound requirements
  are insufficient. This task did not inspect/install or execute those dependencies.
- Review a separate physical-copy allowlist and controlled runtime paths; exclude original
  checkout, seeds/materials/models/data, editable paths and automatic startup hooks.
- Decide and review actual framework construction/route inspection before HTTP acceptance.
  Real FastAPI was NOT instantiated here. No server launcher delivered.
- A synthetic business read path remains separate and unimplemented. A health response
  cannot certify it, authorization, storage, archive recovery or production readiness.

No changes to standard startup, UI or main branch. No package/site/deployment.

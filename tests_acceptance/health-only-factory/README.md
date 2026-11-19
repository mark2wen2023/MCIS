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

## Fixed three-file snapshot plan (no copy or execution performed)
source-snapshot.json fixes Git 0308d07f262ce7436757ade6d16a30fc25c4dd02.
The only permitted payload paths would be:
- mcis_service/__init__.py
- mcis_service/health.py
- mcis_service/health_app.py

The manifest records source path, destination, byte count and SHA-256. All three working
files were byte-compared with exact Git blobs. No other checkout files, main, __main__,
configuration, schemas, models, materials, data or bytecode belong in the source snapshot.
Do not use git archive of the checkout, editable installation, or a checkout on PYTHONPATH.
No copying script, CLI or launcher added. A later separately reviewed copy must verify
exact regular-file set and hashes in a new exclusively controlled directory before imports,
with trusted manifest/root and no symlinks/hard-link aliases/concurrent writers.
Hashes do not establish those preconditions. The package contains no server entry point.

## Existing dependency metadata observation
dependency-metadata.json records 11 distributions, METADATA/WHEEL metadata digests and
full Requires-Dist declarations without importing any target package.
Observer: CPython 3.12.14, Linux x86_64, cpython-312-x86_64-linux-gnu;
resolved observer executable matched the existing venv Python; venv declares 3.12.14.
Read using stdlib-only Python -I -S; no automatic site processing for this observation.

No extras selected. Manually traced base dependency graph:
FastAPI -> Starlette, AnyIO, Pydantic, typing-extensions, typing-inspection,
annotated-doc, opentelemetry-api.
Starlette -> AnyIO and typing-extensions (Python <3.13).
Pydantic -> annotated-types, pydantic-core, typing-extensions, typing-inspection.
pydantic-core/typing-inspection/opentelemetry-api -> typing-extensions.
AnyIO -> idna and typing-extensions (Python <3.15).
exceptiongroup applies only below Python 3.11; not selected here.
Remaining displayed extra-marked dependencies are not part of this no-extra selection.
Observed versions satisfy these displayed base constraints, including pydantic-core==2.50.4.
This is a metadata graph review, not a resolver execution or an authenticated package lock.

Selected installed versions: fastapi 0.162.7; starlette 1.10.0; anyio 4.16.0;
pydantic 2.14.3; pydantic_core 2.50.4; typing_extensions 4.16.0;
typing-inspection 0.4.5; annotated-types 0.8.0; annotated-doc 0.0.6;
idna 3.20; opentelemetry-api 1.45.2.
No .pth/.egg-link names found in this one inspected site-packages directory; selected
distributions have no direct_url.json. This does NOT rule out other startup paths/hooks
or establish official origin, non-editable provenance or absence of unexpected payload.

Still blocked: trusted original wheel provenance/hashes; complete installed file payload
and RECORD comparison; Python executable/stdlib/native shared-library manifests; dependency
import/native closure; namespace-package layout (including opentelemetry); reviewed safe
runtime search paths; actual framework construction and route inspection. Metadata hashes
cannot fill these gaps. No downloads/installations or FastAPI instantiation occurred.
This is health-check preparation only, NOT a runnable MCIS package or startup acceptance.

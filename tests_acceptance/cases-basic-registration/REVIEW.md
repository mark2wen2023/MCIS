# Basic case registration boundary (development check)

Base `a8c6f3036336f8b6a408f3a731de40532aa54433`.

`cases/basic_registration.py::_register_basic_cases(router)` defines and registers the original list/create/get functions, with identical decorators, names, parameters/defaults/annotations and bodies, returning those registered endpoint objects. Existing cases/router.py retains its original APIRouter prefix `/api/v1`, tags `[cases]`, imports, and later overview/vessels/tracks registrations; its original exported function names receive those exact objects. No additional include_router layer or changed main registration. Future caller must supply matching router metadata; no new app factory or endpoint is enabled.

The moved functions now have a different Python module/qualname and are created per helper call. This is not compatibility for monkeypatching old router globals, pickled functions, or custom ID generators inspecting module/qualname. Existing route names, URL/method inputs to default FastAPI operation IDs remain identical; actual FastAPI ID generation/OpenAPI is unexecuted. No permission implementation is copied or replaced.

## Check

`python -B tests_acceptance/cases-basic-registration/check.py`

Passed expanded full-router AST equivalence; exact three function ASTs; existing exported object identity; router metadata, context-default object, response annotations, method/path/status and registration order. Five old/new/basics-only scenarios: normal, synthetic Body-definition exception, and registration exception at each of three basic routes. Original exception sentinel and partial registration order preserved; no exception is swallowed. Full default routes remain list/create/get/overview/get_vessels/create_vessel/get_tracks. Standalone basic module definitions execute only with exact handmade import placeholders; unexpected imports fail, no real dependency code executes. Tests never invoke business endpoint bodies or import FastAPI/SQLAlchemy/app.

## Static dependency boundary

cases/__init__.py, audit/__init__.py and common/__init__.py are empty at this base; service package __init__ is docstring/version. Basic module does not import cases.router, redaction gateway, timeline, evidence, interviews, recommendations or agents overview models.

Still present: cases.service → cases.models (CaseRow/VesselRow/TrackPointRow) → db; audit.service → audit.models/db/common utilities; common.contracts → config/context/jsonschema. Config has environment-backed Settings factories (not instantiated here). Actual case validation lazily reads the schema registry. Database.create_all still imports the full models_registry when invoked. Therefore this is a route registration/import boundary, NOT a minimal schema, pure runtime module, dependency sandbox or startup approval. Future isolated entry needs separate schema/DB/config/authorization review. Existing header-based context is unchanged and is not production authentication.

No service, HTTP, DB/ORM, permission probe, archive, real data, seed, browser or model execution. Real operation IDs/framework introspection/HTTP behavior remain unverified. No main, contract, AI Studio or deployment change.

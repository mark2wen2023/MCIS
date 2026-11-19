# Private app shell extraction — development check

Base: `1366168e77c348a2ae061ef4a885649286e68e35`.

Only the existing FastAPI construction/state/CORS/error handlers/health registration block is moved to `_app_shell._create_app_shell(settings, db)`. The main factory still creates directories, initializes the full database, optionally seeds, then constructs the shell and mounts the same routers. No alternative factory, launcher switch, schema subset, permission option or configuration change.

Run from this checkout: `python -B tests_acceptance/app-shell-boundary/check.py` (requires the fixed base Git object; no fetch).

Development result: complete expanded create_app AST matches the fixed original; six old/new handwritten fake sequences passed (seed off/on, directory/DB/table/seed early failure). Fake state identity, CORS arguments, router order and health/two HTTP error/validation callback outputs checked. Only extracted function AST executes with handmade objects; seed imports replaced with Pass for the fake-only comparison. No source seed module or application module is imported. This does not test real FastAPI, exception dispatch, DB, middleware, HTTP or startup isolation.

The shell imports only FastAPI symbols and the package version. It receives opaque existing settings/db objects and does no directory/database work itself. Main still has full business imports and full initialization; request dependencies remain unisolated. No minimum media entry is connected or started. Startup/archive pauses remain in force.

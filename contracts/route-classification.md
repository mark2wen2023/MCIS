# SEC01 reviewed route surface: build-time check, NOT authentication

route-classification.json lists exact protocol/method/path/endpoint and observed
declaredContext for every current route, including hidden API, framework docs,
WebSocket and mounted surfaces. Current baseline161 method entries =153 API +
8 framework documentation methods;149 API entries use existing get_ctx.
declaredContext only detects the existing declared-role dependency. It is NOT
verified identity, case membership or evidence classification.

Each entry requires explicit scope(case/global/meta/documentation/static/mount),
operation(read/write/export/connect/mount) and nonempty rationale. They describe
the surface, not an allowlist permitting anonymous access. No auth policy or
runtime route behavior is changed by this package.

The pytest gate compares actual route tree to frozen classification. Additions,
removals, changed endpoints/context flags, duplicate protocol/path/method, missing
classification or unsupported traversal fail. FastAPI lazy router prefixes are
resolved recursively; inherited include dependencies require explicit future
inspection support instead of silently assuming equivalence. Hidden routes not
in OpenAPI, docs HEAD routes, static/opaque mounts and WebSockets cannot disappear
from the check. Nested mount routes are inspected where available.

A new route must update the manifest through a reviewed change with scope,
operation and rationale, plus relevant authorization/content tests. Merely updating
the manifest to make CI green does NOT implement or approve access controls.
This gate detects route topology, not implementation-body code changes, reverse
proxy paths, externally added middleware or secret/tenant policy correctness.
Mounted opaque ASGI apps are recorded as mounts; their internal behavior is not
proved safe. Changes there need dedicated review. OpenAPI is not the only source.

CI workflow runs only service tests in a temporary fixture DB, does not start a
listener, deploy, alter auth settings or use secrets. No model call is involved.
Local tests passing does not mean CI ran or that branch protection requires it.
Activation as a required check is a separate repository-owner decision.

Recommended change procedure:
1. Review route/action/data scope, including alternate/hidden paths.
2. Modify manifest intentionally, never automatic snapshot overwrite in CI.
3. Add positive business tests and denied-access tests using the applicable actual
   auth boundary; fixture roles are not production identity.
4. Review resulting diff and run this gate plus business suites.
5. Do not interpret every161 route's inventory presence as security signoff.

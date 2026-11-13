# Independent CLOSED entry placeholder

create_protected_app() is a standalone ASGI application. It returns fixed503
AUTH_NOT_CONFIGURED/no-store for every HTTP request, including health, docs, unknown
paths, HEAD and OPTIONS. It does not read request bodies, parse identity, redirect,
initialize DB/seed, mount the legacy app, or accept WebSockets. There is no enable
switch, auth bypass, route allowlist or temporary identity resolver.

This is a testable deny-all foundation, not completed authentication or an investigator
workflow. The actual CLI and create_app are unchanged and still use spoofable headers.
This placeholder DOES NOT protect a separately running legacy process. No claim is made
that a reverse proxy/tunnel/network setting has been secured or even inspected. Do not
expose the legacy demo service to an intranet. Future production entry selection and
network isolation need separate verification before any protected business route opens.

http-route-inventory.json records 154 OpenAPI method/path operations plus documentation
routes identified separately. Tests detect OpenAPI inventory drift. Denial is universal
and does not depend on this list being exhaustive; direct unknown requests also fail.

No identity tables, login, membership grants, credentials, imported permissions,
production settings, network changes, deployment or formal approval are added.

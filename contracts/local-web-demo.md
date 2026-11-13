# Local fictional web demonstration

Safety design independently reviewed before implementation; implementation reviewed
again. Explicit entry only: python -m mcis_service.identity.web_demo --core-command
<trusted-W2-command>. It binds IPv4 127.0.0.1 at an OS-selected port, prints only local
origin, disables proxy headers/access logging, stops after300s, graceful shutdown25s.
No host/port override, no deployment, no change to default protected or legacy app.

Routes: GET /, /demo.js, /demo.css; POST /run with exactly {choice:"1"|"2"|"both"}.
No case/path/mapping/credentials/command/user data accepted. No generic API proxy.
Each run calls prior run_demo: new temporary fictional case/session, protected
catalog -> selection -> real core -> save/read -> cleanup BEFORE summary response.
Web server stores no account session token. CSRF nonce is separate per-launch anti-
cross-site value, not account token; page memory only, never URL/storage/log.

Exact bound Host and Origin, required nonce, same-origin fetch metadata when present,
JSON64byte budget/5sec body deadline/duplicate-key+header rejection. Reject Cookie,
Authorization, encodings and unknown routes. No CORS. CSP default none, self-only
script/style/connect, no framing/base/forms; no-store/no-referrer/nosniff. No external
assets. Run limits:one active task, five attempts,300s lifetime. Invalid request has
no compute. Disconnect/cancel shields active task; slot releases only at completion,
shutdown waits for cleanup. No browser shutdown endpoint. Existing core timeout15s.
Local same-host tools can access this fictional demo; this is NOT user authentication.

Page renders fixed fictional choices, busy state and summary via textContent. Radio
and button disabled in flight; repeated clicks ignored. Selection change/pagehide
clears results, increments attempt epoch, drops late responses and restores controls.
Responses must match fixed selected IDs/counts and explicit unreviewed/fictional/
not-assessed/nonproduction/cleaned shape. No legacy or mock result fallback.

## Verified and unverified

Actual ASGI+W2 and separate actual CLI subprocess+loopback HTTP returned double-source
5-degree candidate with uncalibrated warning. HappyDOM tests exercise page JavaScript
with controlled responses, not a real browser. CUA cloud browser navigation to the
running loopback URL returned net::ERR_CONNECTION_REFUSED. True browser interaction,
console/screenshot, viewport layout and browser enforcement of CSP/Origin remain
unverified. No public tunnel/hosting or weakened defaults used to bypass that limit.
Local test servers stopped; no live URL is a delivered production endpoint.

Result was temporarily persisted and read, then deleted with the fixture. No durable
case archive, real accident evidence, credential login, IdP, LLM or approved finding.
Ordinary cleanup/error/expiry tested; abrupt OS termination not crash-cleanup proof.

# Unmounted stored-result UI rehearsal

Separate StoredUnreviewedResult display projection, pure transition reducer and
StoredResultPanel. No imports of legacy api/intakeRequest/role, no fetch, credentials,
URLs, browser storage or download. No route mounts; defaults disconnected and
button disabled even when a rehearsal state is supplied. A component is not login.

The future authenticated adapter must supply expected case/run/request/current
source generation independently of the response; assigning expected=raw defeats
context checking. Parser is display consistency validation, NOT authentication.
Whole current generation and request must match, with additional source/parent
hash/incarnation/request-declaration checks. Strict outer envelope and processing
versions; bounded JSON depth/size and finite numbers. Only conflict summaries/counts
and limited IDs are projected; unknown nested fields never reach returned DTO.
No artificial transient sourceBinding; not reused RegisteredResult semantics.
The panel always warns unreviewed/not approved, core implementation not attested,
source count not corroboration, parent relation declaration-only, clocks require
checking. This limited first component does not display every diagnostic detail.

Reducer is pure, no asynchronous/network runner installed. Tests inject actions,
not authenticated responses. Ready is rehearsal only. Each save/read attempt gets
new epoch; repeats while busy ignored, stale responses ignored. Unknown outcome
retains operationId and allows only same-operation retry. A read error keeps known
runId and does not undo save; retries read, never automatic recompute. Invalidate
on case/subject/source/declaration/unmount clears content and increments epoch;
the future host is responsible for wiring those events. No cancellation rollback
claim. Denied/stale require fresh context rather than stale retry.

Tests use synthetic backend result fixture from ASGI/controlled core, not live UI
service, browser, actual W2 in this suite, IdP or LLM. React SSR verifies escaped
presentation and disconnected state, not browser rendering/interactions. Targeted
TypeScript compilation only; this is no claim of whole current frontend build.

Browser transport/login, protected source listing, app routing, CSRF/Origin/Host/
TLS review, live browser flows, full diagnostics view and human review are future
separate work. Default protected backend stays closed. No merge/deploy.

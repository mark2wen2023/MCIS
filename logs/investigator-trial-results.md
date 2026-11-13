# Investigator trial checkpoint

Base fa19715733978fc3e80050236a079b0f350ff662. Product unchanged.
Primary actual-W2 roundtrip1/1, independent repeat1/1, final new1+prior read33=34/34,
zero skips,17.60s. Counts overlap, not additive. Native implementation/reviewer.

Test preparation creates case and registers a fictional CSV via legacy fixture;
local session provisioned directly by trusted host. Actual W2 ASGI save/read/replay
and revocation tested, not full-workbench identity E2E, browser, socket, IdP or LLM.
The Origin denial intentionally remains. UI integration design only, not connected
UI or login. No deployment/merge. See independent report and UI plan.

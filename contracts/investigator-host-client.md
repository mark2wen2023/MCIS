# Runnable trusted-host investigator trial client

InvestigatorTrialClient(db=..., settings=..., session_token=...) is an async Python
client for an explicitly instantiated isolated TrialIdentityApp. HTTPX ASGITransport
executes real routes in process; fixed internal base URL cannot be changed to remote
network service. No CLI, browser, role/operator header, login route, credential store
or token output. Trusted host supplies an already provisioned local session. Token
lives in client memory until close; Python introspection/debugger or host HTTP logging
are NOT protected secrets boundaries. Do not attach logging that captures headers.

Flow: cases() -> sources(caseId) -> select(caseId, validated mapping/declarations)
-> execute() -> saved receipt -> protected read(). select copies/fixes request and
current candidate versions, assigns one operationId. execute does not accept new
parameters; unknown delivery retry uses same operationId. Repeated simultaneous
select/save/read cannot replace active operation. Read failure retains known run ID,
permits separate read retry, never automatically recomputes. close removes local
selection/token and is terminal. Local clear does not undo a saved server result.
Cancellation during save is outcome-unknown, not claimed rollback.
Close is marked before awaiting shutdown; delayed select/save/read responses cannot
revive it. Already committed server records remain even when a closing client drops
its local receipt; retain an operation receipt in the trusted host if later recovery
is needed. This client has no persistent recovery journal.

## Atomic selection precondition

New optional expectedSelection HTTP field is compared to server-owned initial
capture AFTER authorization and BEFORE core/replay/write. It pins case ID/local
incarnation/epoch and every CSV/parent source ID/hash/registration digest/incarnation.
Wrong outer field types reject422; object pins with extra, missing or changed fields reject409. No authority comes from pins.
Client always sends its selected pins; existing legacy trial callers remain compatible
without them, so this is not an assertion all callers now require selection pinning.
Final ordinary source capture still detects changes during calculation. Conditions
are not importable saved results or write grants. Retry with changed scope fails;
user must deliberately select a new operation, not silently refresh versions.

## Running in a trusted host

Use async with InvestigatorTrialClient(...); call cases/sources, pass explicit CSV
column mapping to select, await execute. It returns the current stored unreviewed
result; receipt contains only phase/runId/operationId/status. The session token must
never be given to UI or displayed. This is not an authenticated browser bridge.

Reproducible actual-W2 acceptance:
MCIS_PREFLIGHT_REAL_CORE=/tmp/mcis-preflight-core.sh PYTHONPATH=service
python -m pytest -q service/tests/test_investigator_client.py
(the core command must point to the existing verified W2 wrapper in that executor).

Case/original setup still uses legacy test fixtures and out-of-band trusted host
identity provisioning; afterwards client discovery/selection/save/read all use
protected HTTP routes. Synthetic source data, actual SQLite/ASGI/W2; not real network,
browser/IdP/LLM/production login or user-session delivery. Default protected app
remains closed. No legacy mount, route-deployment, merge or production readiness.

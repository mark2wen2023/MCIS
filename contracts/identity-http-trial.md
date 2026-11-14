# Explicit non-production authenticated save HTTP trial

create_identity_trial_app(db=...,settings=...) is a programmatic integration harness,
not installed by the CLI, environment switches or default create_protected_app.
Default protected entry remains deny-all. The harness does not call/create/mount
legacy create_app. It initializes no database and provisions no user/session/grant.
Host must supply an existing deployment-local SQLite and explicit trusted provisioning.

Only POST /api/v1/cases/{safe-case-id}/timeline/unreviewed-runs exists. Every other
method/path (including docs/export/audit/policy/core/unknown) returns404/no-store;
WebSockets close1008. Legacy X-MCIS role/operator headers confer no authority.
This isolation cannot protect a separately running legacy service; it is not a
network deployment proof. Legacy routes are unmounted, NOT migrated to real auth.

Require one Authorization: Bearer opaque local session, exact application/json,
no cookies, Origin, query string or compressed request. Rejecting all Origin is
intentional for this non-browser trial; it is NOT finished browser/CSRF integration.
Authorize before reading body, then reauthorize in initial/final save transactions.
Body limited64KiB, ten-second total receive deadline, strict duplicate-free finite
UTF-8 JSON, unknown outer fields rejected. No request actor/role/result accepted.
A successful response contains runId/saved/replayed/status only, never raw source
or computed evidence. All outcomes no-store; exceptions do not forward backend
paths, stderr, source content or SQL details. Unexpected save failures report
SAVE_UNCONFIRMED_RETRY_SAME_OPERATION because outcome can be uncertain.

Existing authenticated-save kernel handles same-subject retry, source checks and
session/member revoke/expiry across calculation. The same operationId is required
for delivery retries. HTTP disconnect during body reads does not save; disconnect
after dispatch may still complete server work and requires same-key retry.
HTTP threadpool execution is not cancellable core isolation or a capacity scheduler.
Rate limits, deployment TLS/proxy/Host configuration, IdP/admin provisioning audit,
credential transport/storage UX, result retrieval and browser integration remain.
No default activation, production deployment, approval or formal timeline writes.

# Investigator trial UI integration gates

Design checkpoint at fa19715733978fc3e80050236a079b0f350ff662. This does NOT
connect browser UI, create login, expose credentials, mount routes or deploy.

## Verified current surfaces

Remote api.ts uses X-MCIS-Role/operator from browser state. RegisteredPreviewPanel
uses intakeRequest and transient registeredResult; worksheet.ts emits editable
local unreviewed JSON. None is authenticated saved-run UI. Saved GET instead returns
serverPreview/generationSnapshot and cannot be made a transient preview by adding
sourceBinding. Trial app rejects Origin and Cookie. Browser direct POST is disabled.
Remote blobs inspected: api83793af, panel240e7de, registered596c97f, worksheetb4d4cd4.

## Browser blockers

1. No authenticated browser session delivery/login/logout/revocation or IdP flow.
2. Existing selectable role/operator is not identity and must never become fallback.
3. Evidence/case enumeration still uses legacy endpoints. Merely securing save/read
   does not secure the whole workbench or its source list.
4. No CSRF/origin/Host/proxy/TLS and deployment review. Do not strip Origin in a
   proxy or make a generic privileged bearer bridge to circumvent these gates.

Keep default entry closed. Do not expose test tokens in JS, storage, URLs, source,
logs, exported worksheets or bundler variables. Trusted host provisioning is not
user login. A future server-side bridge still needs authenticated user binding and
per-user/case authorization; it is not authorization by itself.

## Next independently implementable module

A standalone unmounted presentation module, default transport unavailable, contains
no credentials or network endpoints. Separate StoredUnreviewedResult DTO validates
caseId/runId, request declarations, source and parent versions, and explicit
unreviewed/not_assessed/usableAsWriteCredential=false. Only known display fields
projected. No approval/timeline entry control and no unknown field passthrough.

State: disconnected -> ready -> saving -> saved-awaiting-read -> reading ->
read-unreviewed. Distinct outcome-unknown after transport loss permits same
operationId retry; never silently creates a new operation. Read403/409 does not
undo save or silently recompute. Rapid repeats share one in-flight operation.
Case/session-context/source/declaration change or unmount invalidates response
sequence, hides old results and cancels transport where possible. The UI does not
claim cancellation undid an already committed save. Back/reopen must refetch under
current identity before showing content. New deliberate request gets new operation.

## Present deliverable

Actual local non-browser TestClient HTTP POST -> W2 -> saved receipt -> GET current
stored result -> same-operation replay -> read-only member -> revoked session.
Includes valid token + browser Origin rejected. SQLite/session/core are real;
TestClient is not real network/socket/browser/IdP/LLM. One source, synthetic CSV,
not conflict corroboration or validated historical report extraction. No product
change in this checkpoint, no UI-complete/production-security claim.

## Planned acceptance before browser connection

Pure state tests: lost save response, late responses, duplicate click, change-case,
change-subject, changed sources/declarations, close/reopen, read403/409, wrong result
IDs/versions/status/shape and unknown fields. Component tests keep simulated label.
Then independently implement authenticated browser + protected evidence listing,
permissions and transport, review deployment hardening, run actual browser E2E.
Those are future work, not granted by this plan or this test.

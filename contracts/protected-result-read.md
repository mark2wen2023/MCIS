# Nonproduction authenticated current-result read

GET /api/v1/cases/{caseId}/timeline/unreviewed-runs/{runId} exists only
in create_identity_trial_app. Default protected factory remains closed, legacy
application is not mounted or retroactively protected. This is not deployment.

Same-DB hashed Bearer session, enabled subject and current case-incarnation-bound
membership authorize reading. Unlike save, reading does not require the save grant.
No imported grants, cookies, Origin or caller role/operator provide authority.
Current full-content policy and source-intake permissions are additional gates.

Within the reserved SQLite transaction, validate local result index against full
strict-schema audit chain; imported history without current index is 404. Re-read
registered source and optional parent bytes, permissions and incarnations; any
snapshot change rejects instead of recomputing/reinterpreting old output. This
conservative first slice does not provide historical result browsing. Reads use
read permissions, not timeline write permission. It holds a writer reservation for
consistent DB decision but writes no rows/audit/custody, calls no core and grants no
approval. File storage remains mutable; not an immutable-store or crash proof.

Response contains allowlisted run metadata, request, generation snapshots, stored
preview and processing limitations. No audit actor, operationId, session or raw
source text. Output explicitly unreviewed/not_assessed/not a write credential.
Reauthorize after response materialization. Revocation after the authorization
transaction cannot recall data already authorized for return.

Exact GET path only; no list/export/legacy fallbacks, no query parameters, no
cookie/Origin, no body declared by nonzero Content-Length or Transfer-Encoding.
Errors sanitized and all responses no-store. No web login/IdP, TLS/proxy/Host
hardening, live network/browser/LLM, UI, production performance claim.

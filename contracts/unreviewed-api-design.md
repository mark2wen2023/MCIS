# Unreviewed run API design (not enabled)

The default app's X-MCIS-Role / X-MCIS-Operator headers are not authentication.
They MUST NOT authorize this API. No default route or setting enables it.

Proposed narrow POST /api/v1/cases/{case_id}/timeline/unreviewed-runs accepts
only operationId (canonical UUID) and request (RegisteredPreview). It accepts no
computed output, actor, role, case generation, approval or result envelope.
Return only runId, saved, replayed, status=unreviewed; a receipt is not an approval.
No result retrieval, official timeline mutation, evidence modification or approval
endpoint belongs to this slice. Same operationId retries may recover lost delivery
only while actor/input/role/current generations and permissions still match.

A future server-installed adapter must supply an immutable authenticated principal,
CSRF/origin protection appropriate for its authentication method, and authorization
for the specific case. Authentication cannot use the legacy headers. Membership,
principal validity and action permission must be rechecked under the initial and
final reserved writer transactions, including before returning an idempotent replay.
An external identity store with no atomic authorization relationship is insufficient
for this contract; do not silently claim cross-database atomicity.

Fail closed by default. Integration tests can provide fake trusted actors only as
explicit fixtures, never production authentication. Bound input size before parse,
reject unknown fields and duplicate keys, prohibit nonfinite JSON, normalize errors
without source contents, paths or core stderr, and set no-store on every outcome.
Failures after an uncertain commit must say retry SAME operationId; a fresh ID could
duplicate work. UI must not automatically retry with a new key.

Gate: independent review must approve the identity/transaction contract before any
HTTP implementation is registered. Until then internal save remains the only active
entry point, and the investigator-facing workflow is not complete.

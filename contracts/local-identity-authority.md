# Local identity and case-authority kernel (internal integration)

This slice is executable local SQLite identity, not a production login/IdP service.
There is no default user, bootstrap admin, HTTP authentication route, or trusted
X-MCIS header. The independent protected ASGI app still denies every request.
Legacy create_app and CLI remain unchanged and must NOT be exposed as authenticated.

A trusted host administrator explicitly creates a random subject, issues a random
256-bit opaque session (max 24h), and grants a supported case role plus explicit
can_save_unreviewed. Database stores SHA-256 of the high-entropy token, not its raw
value. Administrative functions are internal Python APIs, not self-service signup.
Subject disable, session expiry/revocation, membership disable/action removal and
case incarnation all gate save_authenticated_unreviewed(db,settings,token,...).
Role and audit actor come only from the current local database, never caller role.

Identity, session and membership tables are deployment-local authority. They are
excluded from case archives; restore does not create accounts, recover sessions or
restore memberships. Existing imported role policy cannot create local membership.
Membership binds the local case incarnation, not only a reused case ID. Existing
source/content/timeline permissions remain additional gates, never overridden.

Initial authorization and final authorization reserve the same SQLite database's
writer before reads and verify the transaction/connection/thread reservation proof.
An externally opened deferred transaction is refused, not assumed locked. Initial
transaction releases for core computation; final transaction rechecks enabled
subject, live session, current case membership and versions before output capture
and again before save/replay decision. Changed authority during computation discards
output. Same transaction protects the decision and audit/index write from concurrent
revocation commits. Expiry is checked at decision time; this is not a guarantee of
validity at later network delivery. Wall clock and database integrity are host trust
assumptions, not resistance to privileged DB edits or clock rollback.

Operation replay reauthorizes current identity/permissions and source versions.
A new valid session of the SAME subject may recover the same operation; another
subject cannot take it over. An authorized regrant before a new request does not
permanently poison the operation. No raw token is stored in saved result/audit.

The older save_unreviewed remains a trusted internal compatibility function, NOT a
public API. Python code execution/database-write permission is outside this boundary.
External IdP binding, full old-route protection, CSRF/Origin/body limit enforcement,
credential delivery/storage, authentication audit trail/admin UI and browser flows
remain integration work. No deployment, merge, live LLM or full-system claim.

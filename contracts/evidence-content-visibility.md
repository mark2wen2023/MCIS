# Legacy content GET visibility

GET evidence/{id}/content must apply the same target-case filter_evidence check as GET
evidence/{id}. If the item is hidden by current evidence.restricted Remove or other existing
filter semantics, respond403 FORBIDDEN before filesystem read and Access audit/custody.
Run check within existing BEGIN IMMEDIATE transaction; retain category checks and recorded
digest/container protection. Policy changes committed before reservation take effect;
revocation blocked by an earlier read cannot be called committed. No shortened locks.
Scoped case/id lookup and restored policy use unchanged. This is policy consistency, not
trusted caller identity, SSO or remote revocation of previously exported offline snapshots.

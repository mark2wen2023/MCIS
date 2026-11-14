# Whole-case raw export policy preflight

The target case's server-stored policy is checked inside the existing SQLite reserved
writer transaction. Header roles remain the current unverified local identity model;
this repair is policy consistency, NOT production authentication or authorization.

Always-emitted raw members require ReadOnly/ReadWrite (not Redacted/Deny):
- case.json/case.ext.json/vessels.json, tracks and environment: ais_sim;
- evidence/index.json and raw/evidence files: evidence_meta;
- audit/audit.jsonl, audit/custody.jsonl, audit/agent.jsonl, access-policy.json: audit;
- timeline/time-alignment: timeline; recommendation/consultation arrays: recommendations;
- agents/drafts.json: agent_drafts. Present COLREG member additionally requires colreg.

Preflight checks these categories even when arrays/audit are empty: the response still
contains raw case information/index and generates an export audit. Every scoped document
with a caseId must agree with the target case. Evidence must explicitly bind to that case;
each evidence item must remain visible under filter_evidence, Restricted requires full
testimony access, and VDR additionally requires full vdr_audio. No hidden item is silently
omitted to manufacture a partial backup. Denial before source reads prevents exporting
raw bytes for a revoked category. Unknown/unmapped output members fail closed409.

Existing report/interview/recommendation source/event protections run unchanged before
serialization, including per-draft/source checks. HFACS retains its full-content gate;
working-history export retains its stronger full-content/source validation. The legacy
member check runs before manifest/ZIP creation, within the same transaction. Empty .keep
placeholders carry no content; manifest is derived only from approved members.

Failures return403 PACKAGE_CONTENT_FORBIDDEN or409 PACKAGE_CASE_BINDING /
PACKAGE_MEMBER_UNCLASSIFIED, no package bytes and no committed successful export audit.
Case not found remains404. Policy malformed is rejected, not replaced with defaults;
absent policy uses existing default_policy. Audit denial also applies when no audit rows
exist. Cross-case requests consult only their target policy and rows; embedded caseId
cannot redirect authorization. Old single-read endpoints are not weakened or broadened.

A policy revocation committing before export's reservation is observed and denies. Once
export reserves the writer, concurrent revocation must wait or fail with known-no-commit
503 under the reviewed policy-write path; after commit the next export sees the new policy.
Failure later in serialization/audit/ZIP rolls back the export transaction. Unknown commit
results remain unknown, no automatic retry. Long lock/memory and trusted DB assumptions
are unchanged. Container gating belongs to the separate PR64 integration and must remain.

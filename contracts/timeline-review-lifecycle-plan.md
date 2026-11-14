# Trusted timeline check / human review lifecycle: implementation gate

Status: reviewed design plus existing-model premise tests ONLY. No new database
model, API, authority token, approval, timeline mutation or importer is implemented.
Based on PR56 f1b0c50 (worksheet) and unchanged registered-preview service b5de2a9.

## Why not reuse current confirmation
AgentDraftRow is arbitrary document JSON. agents/router.py applies Confirmed or
Modified timelineEvent by writing a confirmed timeline event. That is not a
receipt-backed observation review workflow. The local worksheet is editable and
must never be accepted as a run/approval credential. Reserved timelineSourceBinding
and timeline-bindings package namespace remain protected. Public reports, hashes,
needsReview=false and user-declared parent links do not establish facts.

The registered intake currently verifies one Register, no Change events, exact
metadata/bytes, permissions and non-historical status. Even a same-SHA Change is
rejected. Access is not a content revision. This permits a narrow initial scope:
new runs over unchanged, locally registered originals only, not arbitrary legacy
or imported/restored sources. This does not solve external disk rollback.

## Minimal staged implementation
A. Save server-owned immutable check run; still unreviewed.
   POST request supplies only selection/mapping/declarations and idempotency key,
   never a computed result/approval/snapshot authority. Server performs the same
   bounded resolve + W2 + exit rechecks, then persists run and audit atomically.
   It returns runId only after commit. No client worksheet import or save-result
   endpoint. The record is a check of a version, not approved observation content.
B. Add human review of that saved run, independent from formal timeline entry.
   Read shows exact frozen sources, mappings, results, diagnostic details and
   explicitly separates parent relationship/observation accuracy from byte checks.
   Review accepts runId, expected review revision, decision and reason, not edited
   result JSON. Changed observations/mappings require a NEW run with supersedesId.
   The prior run and disagreement remain readable; never overwrite old reasoning.
   supersedesId must reference an existing run in the same case/local generation,
   cannot refer to self or create a cycle, and confers no inherited authority.
C. ONLY later add reviewed-observation -> formal timeline admission, with separate
   authority, current source checks and explicit human selection. A calculation
   conflict is not itself a timeline fact. Stages A/B never call AgentDraft._apply.

A is the next shippable slice, but only after its archive/restore and local trust
identity contract is implemented in the SAME change. Do not quietly omit new
rows from backups or whitelist an unsupported populated table. Until then,
local unreviewed worksheet export remains the available save operation.

## Proposed server-owned data (not existing tables)
- check_runs: case ID + local case-generation ID + run UUID; canonical request;
  exact case epoch; immutable result; evidence/Register identities and current
  byte SHA/registration digest; parent snapshots; trusted core build digest and
  contract revision; creator from service identity; server UTC; run digest.
  A digest provides integrity comparison, NOT signature/authority by itself.
- review_events: append-only per-run revision; actor, server time, decision,
  reason, expected prior revision, run digest; unique run/revision and request
  idempotency binding. No general update/delete/import mutation API.
- local trust domain/generation: server-issued identities change for restored
  cases/imports and source recreation. Imported UUIDs are historical assertions,
  not local generation authority. Do not use source SHA alone as incarnation.
  SQLite row IDs/custody seq are supporting evidence, not cross-restore identity.

Initial run tables do not need an Approved state. Review events may later record
NeedsRecheck / Disputed / Rejected / ReviewedForUse; the last means a human review
of identified observations and limitations, not truth or automatic admission.
No reviewer self-approval prohibition is assumed without an agreed policy; record
actor separation so a future four-eyes rule can be enforced explicitly.

## State and invalidation rules
- Computed transient -> SavedUnreviewed: only internal server successful commit.
- SavedUnreviewed -> review event: authorized investigator, exact revision, current
  complete source eligibility, source incarnation and case epoch still match.
- Source/case-version change, review-required flag, registration ambiguity or
  historical restore => effective NeedsRecheck; preserve the old result/event.
- A past review is historical evidence of what was reviewed. It must not silently
  become current again after a change/revert or same-byte recreation.
- Permission revocation => deny read/review now, not expose data by returning a
  stale object. It does not erase old review/audit events.
- Rejected/Disputed cannot become accepted by generic JSON edit. New review must
  reference expected revision and reason; new calculation is a new immutable run.

## Authorization and transaction boundary
Reuse intake.authorize (investigator/lead, full evidence/testimony read and actual
restricted-source access) plus timeline READ. Stage A/B do not require timeline
WRITE because they never change it; formal admission C separately requires
timeline WRITE. Stage A/B persistence needs
explicit write permission for the new review resource, default deny; do NOT infer
it from agent_drafts or silently add it to existing roles/policies. A deliberate
policy migration and its tests belong in the implementing change.
Actual service headers are currently caller-controlled, so prototype checks must
not be advertised as production authentication. Production approval requires a
verified identity provider outside the scope of these local tests.

No transaction held across core calculation. After compute, acquire database write
transaction, freshly resolve sources/epoch/permissions and compare all frozen
identities, then insert run + audit, uniqueness-protected. Review uses an equivalent
fresh check and optimistic revision in one transaction. Database serialization is
not a lock on externally mutable files: trusted byte storage / descriptor-based
reads with protected parent traversal must be designed; fail closed on mismatch.
Do not call existing path/leaf checks an atomic filesystem lease.

Idempotency key is scoped to case-generation, actor and operation. Same key/same
canonical request returns the committed run only after current read authorization;
same key/different request409. Same-key retries must also recheck current eligibility:
if the saved run is stale/historical, return409 (after authorization), not a fresh
success receipt. An explicit authorized history-read route can retrieve the old
run with non-current status, never as the successful current computation.
Timeout without commit does not imply success.
No mixed-success audit/result state; transaction rollback leaves neither written.

## Archive / restore (blocking implementation requirement)
A versioned archive representation must preserve immutable runs and review history,
including their source/reference relationships. Restore marks all as Historical;
no current authority is restored, even if checksums match. Explicit authorized
history GET remains allowed and clearly read-only; active-run GET/review/admission
and save retry reject historical runs with409. Locally regenerated
case/source trust IDs and a fresh new run/review are required for current use.
Restored actor/time are explicitly historical claims. Record the current importer
and import time separately; never relabel them as the original local reviewer.
Old packages with no run history remain valid historical inputs; forged receipt
fields and unsupported namespaces remain rejected. Unknown populated tables must
continue blocking incomplete backups. Tests must demonstrate no silent omission.

## Failure / acceptance matrix for implementation
403: wrong role, missing new-resource write, hidden source, revoked access.
404: case/run absent; no cross-case lookup of run IDs.
409: stale review revision, changed epoch/bytes/generation, same-key different input,
     changed-and-reverted source, same-SHA Change, duplicate/missing Register,
     review-required source, historical run/restore or unavailable trusted core ID.
422: caller result/approval/receipt injection, illegal transition, malformed mapping.
413: bounded input/result exceeded. No partial writes on any of these failures.

Required tests: fabricated run/worksheet cannot approve; no-scope/foreign-case IDs;
permission revoked during compute; concurrent review/idempotency retries; process
failure between insert/audit; same-byte recreation and restore; mutable filesystem
race; archive roundtrip remains historical; stale review cannot apply timeline.
Browser integration must show stale/new versions and preserve disagreement, not
just display a green approved badge. Real model/core/browser/CI claims separate.

## Existing-model premise tests (not lifecycle feature completion)
New tests prove same-SHA custody Change rejects registered preview before core,
while Access preserves byte snapshot but returns persisted=false/not_assessed.
They use actual temporary SQLite/API with controlled core where applicable.
Existing model facts cover registration vs current hash and review flag semantics.
Final test/review result appended below. No merge/deployment.

Independent design review and premise rerun:5 pass, zero skips; one existing
Starlette warning. Review clarified history reads vs active operations, retry
eligibility, READ/WRITE separation, supersession scope/cycles and restored actor
provenance. These are design gates, not verified new lifecycle implementation.

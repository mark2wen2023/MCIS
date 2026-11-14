# Timeline local generation and restore boundary: implementation gate

This is a design/test foundation, NOT implementation of a generation token,
trusted saved run, reviewer approval, or formal timeline admission.

## What existing behavior establishes
A current package-intake retry can return its current local receipt after access
and original-package integrity checks. Re-export encodes that receipt as historical provenance in the new package;
it does not remove or downgrade the current local receipt. Restoring that export must not reactivate the older package-intake key:
a retry of the original package returns ARCHIVE_HISTORY_ONLY. Registered timeline
preview of imported evidence likewise remains historical even when bytes match.
The current import receipt means "this package was imported here", not "the
imported evidence/analysis was locally reviewed".

## Minimal cohesive future implementation
- Allocate a service-generated case-incarnation identifier inside the same write
  transaction that creates a case or restores it. Never use an imported identifier
  as the local incarnation, and do not derive it from caseId or content hashes.
- Legacy cases require an explicit migration/backfill policy. A missing incarnation
  must fail closed for new trusted-save operations, not silently authorize them.
- Bind each saved unreviewed run to local case incarnation, source registration
  incarnation, exact byte/version/metadata snapshots, core identity and request.
  A same-byte replacement or restored record must not inherit trust.
- Allocate source incarnations only at an eligible current registration. Imported
  registration records remain historical. Re-qualification needs an explicit
  permissioned workflow, not toggling a status or replaying a package receipt.
- Add a dedicated write capability (default deny); recheck source read permissions
  and version eligibility inside the final write transaction. Never infer write
  from read permission or an imported policy file.
- Archive run/review provenance with an explicit historical marker and original
  claims. On restore preserve those claims but allocate fresh local incarnation;
  neither historical actor claims nor imported approval become current authority.
- Do not add tables to the archive allowlist without implementing roundtrip and
  historical-only behavior. Unknown populated case tables must block lossy export.

## Atomicity and recovery still blocking trusted saves
Existing import uses SQLite BEGIN IMMEDIATE plus a process-local lock and staging
rename; caught exceptions after publication remove the target and roll back DB.
A test of Session.commit failure validates that ordinary exception path only.
It does not validate SIGKILL/power-loss durability, directory fsync, shared-storage
multi-process exclusion, or external writers swapping paths during compensation.
For trusted-save lifecycle use database-only transactional rows over already
qualified immutable storage, or a recoverable journal with deterministic startup
reconciliation. Do not extend filesystem ownership/cleanup on the strength of
these tests. A UUID is a binding component, not authentication or integrity proof.

## Tests in this slice
`test_archive_generation_boundary.py` exercises two real temporary API/SQLite
paths: two successive restore/export environments with a historical old-key retry,
and a post-publication commit exception followed by successful fresh retry.
No live LLM, actual W2 calculation, real browser, production IdP, new lifecycle API,
CI validation, deployment, or generation migration is claimed by these tests.

Independent review: primary2 plus independent2 pass; permission revocation blocks
historical bytes/current import receipt, restoration of permission does not activate
old evidence. Injected commit failure was observed exactly once after complete source
package publication; all case-scoped DB rows are absent after rollback, current
receipt GET returns404, and retry imports fresh. Focused final31 regression pass,
zero skips. Counts overlap; no CI or crash-durability claim.

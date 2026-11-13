# Local case incarnation foundation (not trusted-run lifecycle)

New cases and both package import entry points allocate a service-generated random
UUID in a separate local table. Case insertion, incarnation record and its audit
marker commit or roll back in the same database transaction. Same-ID creation
remains a conflict. Current import retries retain the existing local identity.
No client-provided or imported identifier is used to create this local record.

## History representation and old data
The complete version1 declaration (caseId, UUID, origin, createdUtc) is stored in
an untruncated snapshot_ref extension of the existing case.create/package.import
audit line. The local row binds its exact audit sequence. Existing package formats
already retain this full audit line: no separate new package field or omitted
identity metadata is introduced. Export validates the row, corresponding action,
entity, sequence, exact declaration and complete audit hash chain before allowing
the operational table. Restore preserves old audit claims as historical content;
it allocates a new UUID and appends a new local import marker rather than rebuilding
current authority from old markers. Imported audit claims are not authenticated
proof of a reviewer, origin or original creation time.

Existing cases and demo seeds are not silently migrated. Their read/export paths
remain available; the internal current-identity lookup returns409 when no local
record exists. Metadata edits do not change identity. No API can set this UUID,
and no new role permission is granted. Orphaned existing identifiers are not
silently replaced. The UUID binds local database identity only, not evidence truth,
review completion or protection against a whole-database rollback.

## Scope and limits
This creates no source-incarnation or immutable-byte store, saved timeline run,
review action, trusted-receipt import or formal timeline admission. It changes no
historical evidence activation rule. Future stageA must still introduce source
versions, explicit default-deny write capability, atomic run+audit/idempotency and
history-only run restoration together. Prototype request headers are not a
production IdP. Database atomicity is not filesystem/process-crash durability;
the older import endpoint still has its existing file-cleanup limitations.

## Verification
Primary5 and independent12 new tests pass; independent combined28 pass. Final74
selected regressions pass, zero skips (overlap), including API/SQLite, ordinary
rollback, both import entry points, two working-archive restores, legacy seed,
metadata PATCH, same-case thread concurrency, injected historical claims and
source-preview/package regressions with existing actual-W2 capability enabled.
An initial independent empty-case permission assumption was corrected using a
real working-history case and normal/corrupt403 controls; no product access defect
was established by that fixture. No browser/LLM/CI/full-suite validation claimed.

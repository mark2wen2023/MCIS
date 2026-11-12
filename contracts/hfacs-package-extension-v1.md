# W18.6 complete local HFACS backup extension

Only the current restricted new-case W8.5 workbench importer is supported. No general
package compatibility, authentication, professional validation, deployment or W11 integration.
Original C# taxonomy/classification sources are unchanged; all tests use synthetic cases.

## Version, complete archive and limits
Optional single member `hfacs/backup.v1.json`, manifest-listed with exact size/SHA256.
Exact JSON: `{format:"MCIS-HFACS-BACKUP",version:1,caseId,
receiptPolicy:"archive-only-on-import",currentDocument,revisionAudit,requestReceipts}`.
currentDocument is the W18.4 saved document or null. revisionAudit contains every full
immutable audit record in consecutive revision order. requestReceipts contains original
`{case_id,request_id,request_digest,operator,response}` records sorted by request_id.
Export unions active and archived receipts, rejecting duplicate IDs. No hidden truncation.
Require one receipt per revision; empty archive has null document and empty arrays.
Engineering budgets: at most256 revisions and256 receipts,16MiB member,32MiB compressed,
64MiB expanded,2048 ZIP members. Exceeding a limit rejects the whole operation.

With extension, manifest packageVersion is exactly1.1.0; without it exactly1.0.0.
Reject unknown versions, unknown fields and any other HFACS namespace member. Legacy
`/cases:import` rejects1.1.0 and any case-insensitive HFACS namespace, including disguised
1.0.0 packages. Only explicitly validated internal calls can restore this extension.
Unity PackageManifest.FromJson reads PackageVersion but does not enforce extension
semantics: older Unity/service readers are NOT guaranteed to reject or preserve these
members. No old-client backwards compatibility or data-loss protection is claimed.
`/packages:verify` checks manifest integrity only, not supported restoration semantics.

## Validation without rewriting history
Strict finite UTF8 JSON, no BOM/duplicate/unknown keys. Check exact fields, case IDs,
consecutive revisions, document digests, full audit hashes/prevHash, before/previous-after
continuity, last after/current equality, role/operator/time/request association and receipt
response links. Fixed Draft/ToBeVerified/Investigator state. Only supported core/taxonomy
versions accepted; actual original CLI validates every distinct draft and classification
must match exactly. Cache identical draft checks within one validation, never regenerate
or overwrite stored classification. Core unavailability rejects safely.
Every historical/current/receipt source ID must be registered in the same-case package.
Historical source titles/hashes remain unchanged even if current metadata differs; this
is not byte revalidation, factual proof or automatic source rebinding.

## Archive-only receipts
Original request bodies were not stored, so request_digest cannot be reconstructed from
sorted saved documents. Validate digest format and receipt/document/audit association,
NOT authenticity of original request digest. Preserve every original field verbatim in
append-only `hfacs_archived_requests`; do not activate imported replay credentials.
Archived IDs are reserved: save with one returns409 REQUEST_ARCHIVED, requesting a new ID.
New requests may update the restored document with expectedDigest and continue the prior
revision/hash chain. Export/reimport preserves receipt values regardless of original store.
Self-reported operator/role labels are not verified identity; no credentials are included.

## Authorization, full-package preflight and transaction
HFACS-containing export requires investigation role and full personal/evidence_meta/
agent_drafts/audit read access, including sources of current document, all historical
before/after documents and all receipts. Default policy is required for this restricted
restorable package. All checks and full assembled-package W8.5 preflight happen before
export-audit append, under WRITE_LOCK and an explicit SQLite transaction/snapshot.
Unsupported nonempty other business modules, changed-original evidence, unsafe IDs or
nondefault policy reject export, never discard content. Denial returns no package and
commits no export audit. Success responses no-store.
Restore same caseId only into a new case/default policy, without overwriting files or DB.
Current document, full audit, archived receipts and import receipt share the existing
SQL transaction; ordinary failure rolls back all and cleans only this operation's staged
files. No crash-atomic SQL/filesystem or multiworker deployment guarantee is added.

## Preview, commit and recovery summary
profile remains MCIS-BASIC-INTAKE-1. All return packageVersion and hfacsExtension: null
for basic1.0.0, otherwise `{version:"MCIS-HFACS-PACKAGE-1",draftCount:0|1,
revisionCount,receiptCount,receiptMode:"archive-only",identityMode:"unverified-self-reported"}`.
Recovery of older stored intake receipts supplements these fields by strictly validating
the retained original archive, without rewriting the receipt. Recovery rechecks all
HFACS historical source permissions; unsupported archive combinations fail closed.

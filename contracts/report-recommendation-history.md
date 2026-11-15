# Recommendation source history v1

New reports carry sourceHistoryVersion=1. Each recommendation citation retains href as
CURRENT register navigation and sourceRef as logical source. Optional historicalSource
contains payload and sha256. Payload is {version:1,caseId,reportId,capturedUtc,sourceId,fields}.
Fields are only present original values among title, addressee, status, dueUtc,
verificationNote, causeNodeIds, evidenceIds; absent differs from null. This is the exact
register projection used during generation, not verified causes or a complete evidence
snapshot. Context and fields are SHA-256 hashed as UTF-8 JSON with sorted keys,
ensure_ascii=False, separators=(',',':'), allow_nan=False. No Unicode normalization.

Snapshots and report audit commit together under existing authorization transaction.
GET/list/export use existing full-content permissions; stored bindings are checked before
return/render. Digest is consistency detection, not signature or protection against an
attacker rewriting both data and digest. Authorization is current, not captured entitlement.
Legacy reports with no version have no guaranteed historical snapshot; UI/export explicitly
say unavailable, and never consult current records to fill history. No migration rewrites.
Unknown version or invalid/missing v1 binding fails 409 report_source_history_invalid.

Scope is recommendations only. Other citations remain current/non-pinned. No change to
recommendation archive restrictions, authentication, long-lock or memory limits. Existing
role headers are not production identity. Old consumers ignore optional properties; strict
external schema consumers must update. PDF/DOCX contain history metadata alongside current
links; JSON report contains full fields. No new HTTP endpoint or automatic retry.

## Audit read follow-up

Report audit-list and report-snapshots reads also verify history recursively in beforeValue
and afterValue (including review sentences/sections). Context comes from the case-scoped
persisted owner report, not the supplied historical payload. Audit event entity and its
snapshot_ref must identify that owner and snapshot row. Regeneration beforeValue is bound
to the owner's parent report; afterValue is bound to the new report. Missing ownership or
inconsistent v1 binding fails 409. Existing content/audit permissions still run first.
Legacy data without v1 metadata and historicalSource is not reconstructed or rewritten.
This does not add a signature over all audit fields or defeat coordinated database edits.
Recommendation archive support remains blocked; no archive permission/format change.

## Strict structural validation follow-up

Protected v1 reads validate report/section/sentence/citation schemas before walking known
slots; missing href/kind/id or malformed structures cannot disable checks. Review values
use their explicit action/section/sentence shape and restore only the intentionally omitted
reviews array for schema checking. Unexpected historicalSource placement fails closed.
Required source inventory and structural identities are compared with stored owner/review
context so removing citations or containers cannot silently discard historical bindings.

Generation audit context also prevents removing the live version marker and all bindings
from turning that report into legacy. Snapshot ownership is recovered via the audit event's
snapshot_ref independently of mutable snapshot reportId/auditSeq; referenced missing rows
block audit listing. True legacy records without v1 history remain unchanged. Coordinated
rewrites of all mutable historical contexts are not defeated by these unsigned checks;
this is not an authenticated append-only object store or production identity solution.

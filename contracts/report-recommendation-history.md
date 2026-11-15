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

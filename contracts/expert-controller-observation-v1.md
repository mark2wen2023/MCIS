# Offline controller observation v1

New wrapper research/expert_budget/controller.py attaches durable metadata checkpoints
to existing main TWO-role Coordination. It does not change the existing Meeting schema,
roles,16/32 shared allowances or600-second cooperative deadline, and does not connect
the separate four-role ledger profile. Full behavior and evidence: CONTROLLER.md.

Single fresh owner per SQLite recording. Return reservations only after committed,
still-active checkpoint. Duplicate controller/restart never resumes or resets budget.
Errors permanently block wrapper; disk observations may be stale after any persistence
failure. No automatic retry/lease takeover. Pending stop/timeout becomes unknown when
checkpoint succeeds. Read-only inspection is never runtime/authorization proof.

Stored metadata excludes review/prompt bodies and credentials. Local sequence/digest
chain is not signed/authenticated. Cap256 changed observations; identical reads are
no-ops. No source/network/process execution. Hard cancellation, token/money budgets,
cross-meeting quotas, authenticated identity and real execution remain unimplemented.
All execution/identity/hardCancellation flags remain false. Product HOLD stays intact.

# Archive export safety A: independent defect disposition

## A1: successful package transfer silently omitted report state

Confirmed on the pre-fix synthetic baseline: actual report API creation returned201, export200 and old import into a fresh database201, while restored ReportRow and ReportAuditRow counts were both zero. Reports, family versions and review snapshots therefore were not safely backed up by nominal package success.

## Final disposition

**Resolved by explicit refusal for the scoped known unsupported content, not by implementing restoration.** Independent 18 API/DB tests and actual-service browser passed; all12 frozen file hashes matched. Cases containing report documents, report-operation snapshots, transcripts or identified residual report/interview audit now receive409 after existing authorization/source checks and before assembly/audit writes. Orphan manual receipts keep their dedicated refusal. Unauthorized callers receive403 without archive-state detail. Logical table and non-database file comparisons show no refusal side effects.

Basic-case export remains usable. Old import, HFACS path and shared writer-proof implementation were not changed. Independent HFACS restoration was not re-exercised in this acceptance slice. No claim is made that other unexamined module state can be fully restored. A future versioned working-record archive must independently prove completeness, permissions, inert historical receipts and cross-table/file rollback.

See `tests_acceptance/ARCHIVEA/REPORT.md` for precise scope. Private reproduction scripts and raw execution logs are excluded from publication.

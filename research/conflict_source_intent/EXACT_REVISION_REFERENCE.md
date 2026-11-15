# Exact captured revision read prerequisite

Base1350a4ce367de2fdef6499943a7db9b3619ab555 inherits backend58720e6,
frontend6102b0b and actual HTTP harness8b69e21. Independent candidate, not main.

Implemented: standalone MCIS-CONFLICT-REFERENCE-1 JSON schema and explicit GET
/conflicts/{id}/revisions/{revision}?sha256=... . Calls the existing
conflict_revisions function unchanged before selecting/digest-comparing. Therefore
same WRITE_LOCK/SQLite transaction, case/timeline/content/current source policies,
chain/audit checks as whole-history read. No direct database shortcut. Return is
subset of already-authorized history plus false verification flags; no file reads.
This does not establish production authentication; role headers remain self-reported.

Report citation schema/generator/UI untouched. New standalone reference is not
silently accepted as report citation. Existing reports/legacy citations unchanged.
Unknown legacy history returns404 for exact reference; no invented historical hash.

Ordinary developer tests from service/:

    PYTHONPATH=.. .venv/bin/pytest -q tests/test_conflict_exact_revision_reference.py tests/test_conflict_report_citation_gap.py tests/test_observation_receipt_http_integration.py

Final9 passed in2.26s:6 new exact-reference cases plus1 existing report-gap diagnostic
and2 controller/real loopback HTTP tests. Synthetic temporary SQLite only. Exact
lookup survives registryA->B and observation revision2->3, preserving capturedA;
unknown revision404, mismatched supplied digest409, invalid parameters422, legacy
unrecorded history404. Old report creation still works and still lacks conflict
citations, explicitly verified by the gap diagnostic. Not corruption/permission
mutation/ECFC tests. No restricted checks retried.

First run8failed/1passed because new schema lacked mandatory$id and shared schema
registry initialization raised during writes. Added official local schema$id,
then entire selected group passed; production schema loader not changed.

Unresolved report integration blockers:
- working_records_archive/service.py ALLOWED_TABLES does not support conflict
  revisions/receipts; validation.py citations has no registered conflict reference
  resolver or restoration contract. Do not add whitelist entries without full state.
- A report citation must preserve exact binding through sentence edits, report
  history/snapshots and export/restore. Existing report.schema citation enum and
  additionalProperties restriction deliberately unchanged here.
- Need complete versioned lossless conflict current/revision/audit/receipt/source
  associations and legacy policy before enabling report generation. Historical
  original bytes are not available/verified by registry receipts.

No full report provenance feature completed. No new report content generated from
observations, no automatic conclusion confirmation, no archive protection loosened.
Real browser, independent permission/concurrency review, full archive roundtrip,
production identity and originals remain unverified. No merge/deploy.

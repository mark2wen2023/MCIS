# W16 synthetic production DOCX slice

Parent: `68a171f41ed0da9029a9dfff80b4231cbadb6044`.
Only this runner and runbook are added; no product source changes.

From repository root, using an existing environment containing python-docx and
ReportLab (observed Linux: python-docx 1.2.0, ReportLab 5.1.0):

```sh
/path/to/existing/venv/bin/python -I -B tests_acceptance/w16-docx-synthetic/check.py
```

Five first-party files are SHA-256 pinned in the runner. It imports the actual
`reports.exporter.export_report` through normal Python imports. A fail-closed
import guard prevents other mcis_service modules from loading; it does not
replace modules or extract functions. No app, service handler, database, seeds,
model, network, authorization changes or generated report are involved.

One explicitly fictional draft is supplied directly to the exporter. This is
not proof of report generation or source authenticity. Its pending-source text,
zero-valued text and citation flags are authored test inputs, not new policy.
The exporter produces a real temporary DOCX. ZIP integrity and document XML
readback verify two bilingual rows in the correct columns, pending/zero text,
missing/review citation labels, draft/fiction labels, header and disclaimer
footer; input remains unchanged. The temporary DOCX is deleted automatically.
No produced DOCX, report data or output receipt is committed.

Observed: 1 integration test passed, exit 0. This is DOCX package-content
verification, not Word/LibreOffice layout, font embedding, PDF, HTTP, database,
report generation, save/reopen, signing, finalization or archive acceptance.
No browser, service or CI required. No export is published or sent externally.

# W16 synthetic production DOCX slice

Parent: `68a171f41ed0da9029a9dfff80b4231cbadb6044`.
Original slice added only the runner and runbook; see the continuation below.

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

## Continuation headers (parent 1ab1c87940258f4725e1add4afdf55afe0f44488)

Only `_repeat_docx_header` and its two DOCX call sites are copied from
b4df82306d9bab87b938b9e447e27a64b0464406. PDF, titles, text policies and other
business behavior are unchanged. The original runner's exporter SHA is updated;
its assertions are unchanged.

```sh
/path/to/existing/venv/bin/python -I -B tests_acceptance/w16-docx-synthetic/check.py
/path/to/existing/venv/bin/python -I -B tests_acceptance/w16-docx-synthetic/check_long.py
# Optional: generate a local synthetic file for independent office layout review.
# Target must not exist; never commit the output.
/path/to/existing/venv/bin/python -I -B tests_acceptance/w16-docx-synthetic/check_long.py --output /tmp/mcis-synthetic-long.docx
```

The long example contains 80 substantial bilingual rows and the unchanged real
glossary. Both tables' first rows have exactly one continuation-header marker;
all content rows have none. Every sentence is read back in its original column
and order. Draft/missing markers remain. The old exporter failed the header
assertion (exit 1); the patched exporter and original check both pass (exit 0).
No layout engine has run: actual page count, continuation appearance and clipping
remain for independent LibreOffice/Word review. The fixed glossary itself is not
expanded to force it across pages. Default run retains no DOCX artifact.

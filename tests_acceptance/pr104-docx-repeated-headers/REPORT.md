# DOCX repeated headers — developer candidate, awaiting independent review

Base local ac68529 (office review records), whose parent243208d adds only regression records above PR104 head1651b98. No runtime changes in those intervening commits. Branch fix/pr104-docx-repeated-headers. PR104/main unchanged, not pushed/merged/deployed.

Confirmed OOXML gap: no tblHeader on first row. Add repeating header to bilingual section and glossary tables. Section English label now explicitly includes original-language excerpts and states they are not fully translated. No translation generated. No stored sentence, original quote, citation, evidence, audit, role or permission change. English-only/PDF renderers unchanged; public-excerpt preface already says original Chinese is retained and is not an official English translation.

The first render of this change introduced a page2 orphan heading because the intervening missing-data paragraph did not keep with its next content. Fixed that DOCX paragraph formatting, not text. Final page2 no longer has section3 title; section3 begins page3 with body. Long rows may still span pages, dense references and font substitution remain.

## Tests
From service/:
```
./.venv/bin/pytest -q tests/test_report_docx_headers.py tests/test_report_sentence_source_status.py tests/test_report_modified_citation_disclosure.py tests/test_report_public_pdf_layout.py tests/test_reports_w16_export.py
```
Final31 passed in8.66s. Two new tests inspect real public-fixture DOCX OOXML header semantics, no header markers on body rows, exact unchanged sentence/citation display, unchanged input object, missing-notice pagination flag, glossary and no-glossary paths. Existing29 regressions retained. First command had an incorrect test creation path, exited4/no tests; corrected before final runs. Earlier31 passed before the pagination follow-up is not the final result.

## Actual office rendering
Reuse exact prior public report.json from /tmp/mcis-public-pdf-ze9v9bsj, render_docx(report,'bilingual') to /tmp/mcis-pr104-docx-headers/public-report.docx. No new public scenario/model run, no private data.
```
soffice --headless --convert-to pdf --outdir /tmp/mcis-pr104-docx-headers /tmp/mcis-pr104-docx-headers/public-report.docx
pdftoppm -scale-to 900 -png /tmp/mcis-pr104-docx-headers/public-report.pdf /tmp/mcis-pr104-docx-headers/page
pdftotext -layout /tmp/mcis-pr104-docx-headers/public-report.pdf /tmp/mcis-pr104-docx-headers/rendered.txt
```
Existing LibreOfficeDev26.8.0.0.alpha0 build2c87e51eeaa2b413ff4ae097b2705eea1995d8e5, normal installed wrapper. Conversion exit0, same three font-cache warnings. Final23 Letter pages vs original22. All23 PNG pages saved locally and viewed in six overview sheets; initial changed pages2/11 enlarged, then final overview checked for pagination. Text extraction additionally confirms repeated header/caveat on all19 pages containing section tables and section3 moved from page2 to3. This supporting extraction does not substitute for visual review. Source public report/digests remain in previous office record; final output hashes in adjacent manifest. Images/DOCX/PDF/reportJSON/tempDB are not committed.

Developer review only; no independent candidate review yet. No Microsoft Word, stable LibreOffice, browser, full CI, HFACS, real model or production identity verification. No installation or safety change. No restricted tests retried. Do not add31 to prior overlapping selections.

# Investigator-edited sentence citation disclosure — developer verification

Base: db928a217c975c36062038b864b93a387ce622f3 on the independent
fix/report-sentence-source-status branch, itself based on PR104 head
88cc9fdc4ed59704a1777aa58b0e16e058cf9220. PR104/main are not modified.

## Scope
UI and shared PDF/DOCX sentence renderer visibly explain that inherited citations
provide traceability context and do not automatically substantiate edited wording
or identify it as an original quotation. Human support review remains necessary.
The condition is source=Investigator with citations, including stale sourceStatus
and later Confirmed/Dismissed states. Generated sentences and missing citations
are not falsely labelled. Chinese, English and bilingual modes are covered.
No persisted body/generatedText/citations/audit edits, old-data migration, evidence
reading or permissions change. This does not implement automatic evidence checking.

## Executed ordinary verification
From service/:
```sh
./.venv/bin/pytest -q tests/test_report_modified_citation_disclosure.py tests/test_report_sentence_source_status.py tests/test_reports_w16_direct.py tests/test_reports_w161_snapshot.py tests/test_reports_w16_sources.py tests/test_report_cause_provenance.py
```
Result: **99 passed in 29.20s**, including eight new cases (six renderer cases and
two actual HTTP PDF/DOCX exports). Public YANGZE report fixture with explicitly
synthetic investigator wording; no private originals or model invocation. Export
assertions retain references/generatedText and verify persisted report unchanged.

From web/:
```sh
npm run test:w16
npm run build
```
Result: **182 SSR assertions passed**, TypeScript/Vite build passed. Existing large
chunk warning remains. These are developer tests, not independent acceptance.

Initial expanded run: 98 passed, one PDF text extraction assertion failed because
default pdftotext interleaves bilingual columns. Actual output contained the full
notice; pdftotext -raw preserves content-stream order. The final test retains full
Chinese/English notice assertions after whitespace normalization. No product
relaxation or deleted assertion was used to obtain the final result.

## Limits
No actual browser interaction, complete PDF visual acceptance, CI, real LLM/HFACS
or production identity verification. Text extraction and SSR are not visual/browser
acceptance. No previously restricted security/ECFC/integrity tests were attempted.
This commit remains local pending review/push authorization; no merge or deployment.

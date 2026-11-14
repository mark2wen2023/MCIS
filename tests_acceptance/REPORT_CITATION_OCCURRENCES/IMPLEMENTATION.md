# Report citation occurrence trace — implementation evidence

Base: main `3aba2bf03e393909c611489ae573a887087637ac`.
Scope: existing PDF/DOCX report rendering; no endpoint, schema, persistence, source lookup, model call, or attachment change.

- Inline snapshot-local sentence/citation positions link to every occurrence's appendix declaration.
- Identical summary entries may collapse; conflicting registration/review flags and repeated occurrences remain visible.
- Missing fields and sentences without citations are explicit. Positions do not certify evidence, authorship, support or facts.
- Existing report download bundle remains the byte-binding mechanism; callers should retain it.

Validation (service/.venv):

- `pytest -q service/tests/test_report_citation_occurrences.py service/tests/test_reports_w16_export.py service/tests/test_reports_public_provenance_export.py`: **29 passed** (r1).
- `pytest -q service/tests/test_reports_w162_legacy_synthetic.py service/tests/test_reports_w162_access.py service/tests/test_report_output.py`: **245 passed**.
- Generated bilingual PDF using synthetic, explicitly fictional fixture; inspected rendered page with pdftoppm. Markers, bilingual text, draft watermark, conflicting flags and appendix remain legible.
- Both PDF text extraction and DOCX XML readback exercised across zh/en/bilingual. Escaping tests ensure literal hostile metadata and no DOCX external link relationships.

Independent review identified PDF whitespace collapse in trace metadata; r1 escapes literal whitespace as JSON Unicode escapes, preserving distinctions without changing source text. Added PDF/DOCX regression tests. The 56-test download bundle suite passed again after r1. Original freeze is superseded by `logs/report-citation-occurrences-r1-impl-hashes-frozen.txt`.

Limits: no browser/session walkthrough, office GUI DOCX layout, live evidence retrieval or model capability acceptance. Synthetic fixtures validate rendering only. No merge or deployment.

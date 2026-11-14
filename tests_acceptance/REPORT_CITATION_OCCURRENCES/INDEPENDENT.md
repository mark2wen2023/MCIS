# Independent citation occurrence export acceptance — 2026-11-14

Separate native reviewer, limited to exporter/citation_trace plus independent tests. No implementation, branch, unrelated module or research files changed. No model call, network source lookup, commit, push or deployment by reviewer.

Found and fixed RCO-D01: actual PDF readback collapsed significant spaces in section/sentence/source declaration strings. Example initial `sourceRef="line  two  spaces"` became `sourceRef="line two spaces"`. The implementation owner introduced trace-only JSON whitespace escapes and documented them. Independent readback now decodes JSON scalars and matches the original values. See DEFECTS/REPORT_CITATION_OCCURRENCES.md.

**20 independent tests passed**, using actual generated PDF and DOCX bytes. Combined focused exporter regression: **47/47 passed, zero skips** (20 independent plus27 existing/new exporter checks). The revised freeze `logs/report-citation-occurrences-r1-impl-hashes-frozen.txt` matches all4 files.

Independent coverage:

- PDF/DOCX metadata values preserve consecutive spaces, NBSP, tab/newline, quotes, ampersands and markup literally after JSON decoding. Input report snapshots remain unchanged.
- Two sections with duplicate section/sentence IDs retain distinct one-based sentence and citation occurrence positions. Identical repeated citations are not collapsed in the occurrence list. Both bilingual columns use the same snapshot position. Exact marker counts prove every rendered use and appendix entry survives.
- Contradictory registration/unregistered/needsReview declarations remain visible; summary deduplicates only identical declarations. Neither registered nor missing declarations are promoted to verified facts.
- Empty `sentences:[]` and absent `sentences` both use the legacy fallback consistently, preserving section ordinal and explicitly reporting absent sentenceId/no citations.
- Missing flags, false flags, null and empty-string source declarations remain distinct.
- Socket creation is prohibited during rendering; source URLs remain literal. DOCX contains no external relationships/hyperlink elements; PDF contains no link/URI annotations. Existing source-support/authorship/fact disclaimer is present.

Reproduce:

```sh
service/.venv/bin/pytest -q tests_acceptance/REPORT_CITATION_OCCURRENCES/test_independent.py service/tests/test_report_citation_occurrences.py service/tests/test_reports_w16_export.py
sha256sum -c logs/report-citation-occurrences-r1-impl-hashes-frozen.txt
```

Limits: PDF was independently extracted with `pdftotext -layout`; DOCX was reopened with python-docx and ZIP/XML inspected. This proves output content, not visual acceptance in every PDF/Word reader, accessibility or pagination at every extreme. Reviewer did not perform a separate visual screenshot assessment. No new source resolution, registration, content-byte authenticity or semantic review was tested or claimed. General endpoint access/bundle tests are reported separately by the implementation owner.

# Public report PDF layout — developer review, independent review pending

## Exact baseline and scope
Checked remote main=94d5e38c926fda232bb987b60fa9145e4bcf01a7 and
PR104=88cc9fdc4ed59704a1777aa58b0e16e058cf9220. Independent branch
fix/report-public-pdf-pagination starts at bbafa560c71f247eecd64eaaa76c29b9fed700b2,
which includes the two report source/provenance presentation fixes above PR104.
PR104 and main are not changed. No permission, raw evidence, review history or
archive behavior changes. New source display changes require generating a new
report; old stored reports are not silently rewritten.

## Findings and minimal changes
- All 18 baseline PDF pages were rendered and viewed by the developer. Section
  headings 6 and 9 were separated from their body at the bottoms of pages 4 and 6.
- PDF now reserves measured heading/notice plus a short body beginning before
  placing each section. References/glossary headings keep with their next item.
  First attempt used keepWithNext for a whole table: it passed geometry assertions
  but visual review revealed excessive whitespace/23 pages. Replaced with bounded
  conditional page breaks; final actual sample is 18 pages.
- Pinned source excerpt display omits exactly nine standalone page-footer tokens:
  2,11,12,14,16,22,27,44,47. Each is immediately before a form feed and equals the
  original body page (PDF page minus two front pages). Raw quote, source hash,
  physical line ranges and page references are unchanged. Ordinary footnote
  markers 6/7 and all other source numbers remain. No inference for unknown files.
- Original captions for figures 4/8/14 remain with an editorial note that the image
  is not included and the original must be consulted. No image is invented or
  reproduced. Generation preface discloses display normalization and footer
  omission. Draft, needs-review, limited excerpt and no new liability finding stay.

## Reproducible execution
From service/ (uses existing project virtual environment and system Poppler):
```sh
PYTHONPATH=. ./.venv/bin/python ../tests_acceptance/report-public-pdf-layout/render_sample.py
# The script prints a fresh temporary output directory. In that directory:
pdftoppm -scale-to 1100 -png public-report.pdf page
pdftotext -bbox-layout public-report.pdf layout.html
```
This uses the actual local FastAPI TestClient, public seed and authorized test
principal; no LLM/HFACS invocation, real SSO or private case originals. Temporary
SQLite and exports are NOT committed. PDF timestamps/report IDs make byte hashes
run-specific, not deterministic reference outputs.

```sh
./.venv/bin/pytest -q tests/test_report_public_pdf_layout.py tests/test_reports_w161_public_text.py tests/test_report_modified_citation_disclosure.py tests/test_report_sentence_source_status.py tests/test_reports_w16_direct.py tests/test_reports_w161_snapshot.py tests/test_reports_w16_sources.py tests/test_report_cause_provenance.py tests/test_reports_font_coverage.py
```
**111 passed in 34.73s**, including three new tests. Focused three passed in 1.95s
(they are included in 111, not additive). New tests verify raw coordinates/hash
preservation, numeric/footnote safeguards, real caption notes, all 17 section
headings sharing a PDF page with their first sentence beginning, review notices,
and unchanged persisted report after export. Existing actual PDF/DOCX and
modified-citation regressions pass. No new skip, fake core or relaxed permission.

## Final developer visual review (all 18 pages, not independent acceptance)
| Page | Observations |
|---|---|
| 1 | Title, case fields, draft and disclaimer legible; two-column excerpt begins. |
| 2 | Overview continuation, terminology and ship-section heading/body retained. |
| 3 | Ship fields and weather; original footer 2/11 absent, source text retained. |
| 4 | Weather continuation and hull; figure 4 explicitly says image absent; no orphan section 6 heading. |
| 5 | Section 6 starts with body; collision timestamp text retained without footer 14; steering starts. |
| 6 | Steering continuation/figure 8 and helm/figure 14 visibly marked; no orphan section 9 heading. |
| 7 | Section 9 begins with body; source quantities retained; events heading/body together. |
| 8 | Events/emergency response continues; original footer 27 absent. |
| 9 | Emergency/losses/analysis sections legible; analysis starts with missing-data caveat. |
| 10 | Existing what-if descriptions and sources continue; derived/reference-only labels retained. |
| 11 | Existing what-if/assumption content; no observed overlap or truncation. |
| 12 | Existing model assumptions continue; references retained. |
| 13 | Assumptions and attributed cause excerpt; original footer 44 absent. |
| 14 | Attributed liability/issues excerpts; footnote 6 preserved, not treated as page number. |
| 15 | Issues/disposition; footnote 7 preserved and original footer 47 absent. |
| 16 | Safety-management text, missing-source caveat and references beginning. |
| 17 | References readable but dense; long hashes/URLs wrap. |
| 18 | Remaining references and full glossary fit with disclaimer/footer. |

No observed clipped body or missing glyphs at the rendered review size. Existing
ReportLab table splitting may repeat column labels within a page; dense references,
wrapped URLs, source-excerpt line breaks and footnote layout remain. This is not a
full typesetting redesign or proof of source accuracy. The final PDF was generated
from a new report; existing persisted report text keeps its historical formatting.

Local final PDF: /tmp/mcis-public-pdf-layout/public-report.pdf
SHA256=e13f3f69daa6d24fdffdde959b2cddc2089c619aafbfaaa6e3891dfe331cdc4a
Local original PR104 sample SHA256=96e85702cb39198428d5f50c8349d6ce297d541c16bdf9fceba9499336f3b09b
Public text SHA256=bca8f8b8ba04a5d0669a121bc6c9380c8cd6f8397f67be2d0b30b38871c22ef2

No browser, independent visual review, production identity, full repository CI,
real HFACS or model acceptance. DOCX text regression is not Word visual review.
No restricted security/ECFC probes, external APIs, deployment or merge.

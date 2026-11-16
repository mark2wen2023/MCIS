# PR104 DOCX actual office rendering — developer review only

Date: 2026-11-16. Remote main94d5e38c926fda232bb987b60fa9145e4bcf01a7; Draft PR104 head1651b98d221611d25aca6828676e43f892da9b6d re-read unchanged. Local parent243208d158da8da4565545109bf1639f3cdfa171 adds acceptance records only; runtime code is identical to PR104. No runtime repair was made in this review.

## Actual execution

Existing installed `soffice --headless --version`: LibreOfficeDev26.8.0.0.alpha0, build2c87e51eeaa2b413ff4ae097b2705eea1995d8e5. The provided wrapper invokes bundled native LibreOffice with a temporary profile. No installation, network service, credential access or security setting change.

From service/:
```
PYTHONPATH=. ./.venv/bin/python ../tests_acceptance/report-public-pdf-layout/render_sample.py
```
This uses the existing public YANGZE22 fixture and authorized test principal, real report-generation/export code and isolated temporary storage, without LLM or private originals. New output directory: /tmp/mcis-public-pdf-ze9v9bsj.

```
soffice --headless --convert-to pdf --outdir /tmp/mcis-pr104-docx-review /tmp/mcis-public-pdf-ze9v9bsj/public-report.docx
pdftoppm -scale-to 1100 -png /tmp/mcis-pr104-docx-review/public-report.pdf /tmp/mcis-pr104-docx-review/page
pdftotext -layout /tmp/mcis-pr104-docx-review/public-report.pdf /tmp/mcis-pr104-docx-review/rendered.txt
```
Conversion exit0, Writer/writer_pdf_Export. Three `Fontconfig error: No writable cache directories` warnings were retained. Output22 US Letter pages,745758bytes, taggedPDF1.7. This is office-rendered DOCX, not the separately produced ReportLabPDF. ReportLab's18pages/A4 does not establish identical pagination.

Input DOCX SHA256: d0969581e9a4fab88dab8a2f1585bf50719985354646359174557ec260ba0cbc.
Office PDF SHA256: c3dbe5d550d0f07351d194d35b5bcb2d4d99c1eeecc22924f9998460c05fc726.

## Visual evidence and observations

All22 individual PNG pages are saved under /tmp/mcis-pr104-docx-review/page-01.png through page-22.png. Six contact sheets cover all pages. Developer viewed each page in those overview sheets and enlarged individual pages1,4,6,11. An earlier six-image tool response was truncated and was not counted as inspection; subsequent smaller sheet/image calls were viewed. No independent office visual reviewer has checked this sample. This is not exhaustive word-by-word proofreading.

| Pages | Observed |
| --- | --- |
|1–4| Title, overview, terminology, vessel/environment and hull sections; headings have following content. Tables continue across pages. |
|5–8| Hull continuation, collision time/location, steering/helm and pollution; missing-image caption notices visible. |
|9–12| Event/emergency/loss and analysis sections; dense source digests and derived-value text wrap inside columns. |
|13–16| Analysis assumptions, responsibility/issues and recommendations; explicit quoted-source/needs-review limits retained. Footnote6 is retained, not treated as a page number. |
|17–20| Recommendations and references; dense URLs/digests wrap and some reference paragraphs continue on next page. Footnote7 retained. |
|21–22| Remaining references and glossary; final page has usable whitespace, not a blank trailing page. |

No confirmed severe clipping, overlap, orphan section heading or isolated original page-footer was identified at these review scales. This is not a guarantee of absence. No scope-expanding cosmetic change was made. Known usability limitations: continued tables do not repeat language column headings; references are dense; long rows and reference paragraphs split across pages; table cell padding is small. Missing images remain explicitly absent, not restored.

pdffonts shows substituted embedded NotoSansCJKhk/Carlito/NotoSans/NotoSerif fonts rather than the requested NotoSansSC. Chinese glyphs are visibly rendered in inspected areas; exact intended-font fidelity is not established. Alpha Writer output cannot stand in for stable LibreOffice or Microsoft Word compatibility. No browser, print-device or PDF accessibility validation.

## Ordinary regression

From service/:
```
./.venv/bin/pytest -q tests/test_report_sentence_source_status.py tests/test_report_modified_citation_disclosure.py tests/test_report_public_pdf_layout.py tests/test_reports_w16_export.py
```
29 passed in6.66s, exit0. Developer regression only; overlaps earlier selections and must not be added to their totals. No HFACS/realCLI/model execution and no restricted security/ECFC test retried.

Artifact hashes are in artifact-sha256.json. Rendered files remain local, not committed or uploaded; manifest contains only names and hashes. Runtime code, permissions, original evidence and report history unchanged. PR104 remains Draft/DO NOT MERGE. No push, merge or deployment in this turn.

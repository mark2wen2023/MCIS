# Fixed public report text line location (candidate)

Scope: the existing YANGZE 22 public-text citation, not a generic evidence viewer.
The original case evidence-entry link remains. A second, explicitly external link
opens reports/yangze22/report.txt at a fixed Git commit and LF line interval.
The source SHA256 and declared PDF/body page interval must match the checked index.
No quote search is used: repeated text remains distinguishable by line numbers;
cross-page intervals retain both bounds. Form feeds count as page boundaries,
not extra LF lines. The index is checked against the real public text and all 17
backend excerpts. Unknown versions, cases, unregistered entries or malformed
locations receive no new link; original sourceRef remains available.

Pinned source commit: c6113bee85d25bf97d805fb2d264fb6ab138b2e2.
SHA256: bca8f8b8ba04a5d0669a121bc6c9380c8cd6f8397f67be2d0b30b38871c22ef2.
This identifies the public text version, NOT the current evidence object's version
or authenticity. It does not certify that a quotation agrees with its declared
interval. It does not import/store/open the PDF or implement PDF page navigation.
The GitHub link requires external network access; no private case data is sent in
its URL. Existing server permissions are unchanged. New links require matching
loaded report/case and an unblocked view. No new service endpoint or authorization
policy is introduced. Other evidence formats and versions remain unsupported.

## Developer validation

- web: esbuild tests/public-text-location.test.tsx --bundle --platform=node
  --format=cjs --jsx=automatic --outfile=/tmp/public-text-location.cjs;
  node /tmp/public-text-location.cjs: 26 assertions (actual public text plus
  constructed invalid inputs and SSR).
- web: npm run test:w16: 148 assertions.
- web: npm run build: TypeScript and Vite pass; existing large-chunk warning.
- service: .venv/bin/pytest -q tests/test_public_text_location_index.py
  tests/test_reports_w161_public_text.py tests/test_reports_w162_access.py:
  86 passed.

These are developer self-tests, not independent acceptance or full-suite results.
No real browser/GitHub anchor interaction, real model, OCR or PDF viewer tested.
No restricted historical integrity verification performed. Main base 94d5e38;
open PR93/95 sources.py changes are not included. Additive progress documents may
conflict on merge and must preserve both histories.

## PR103 terminal-page correction

Independent review found L1156 (only a terminal form feed) was incorrectly
accepted as PDF54/body52. The pinned index now declares pdfPageCount=53;
locations beyond that bound are rejected, including ranges ending on L1156.
No clamping or remapping to page53. Internal form feeds remain in the index:
blank physical lines keep their page and interior empty pages are not collapsed.
Actual source has no empty physical page; the empty-segment check is synthetic.
All interior body-page crossing ranges and the final real page are regression
checked, plus rejection of both PDF54 and a falsely relabeled PDF53 terminal line.

Local pdfinfo confirms 53 pages on the public PDF SHA256
99084b8e672da6e2f8d9809bea25a92fe5fcf31c318554832e14339610015d7f.
The optional pypdf import was unavailable; no dependency was installed.
Final developer rerun: 32 counted frontend checks plus source/page-boundary
assertions, 148 W16 assertions, 87 backend tests, build pass (same chunk warning).
Browser interaction and independent re-acceptance still pending. No PDF uploaded
or production permission/backend change.

## Always-visible disclosure follow-up

The link's visible text now explicitly says “未核验当前证据版本” and
“未自动核对引文内容，请人工复核”. These limitations no longer depend on
hover/title access. SSR regression strips HTML tags and attributes before checking
both disclosures and the human-review instruction. No location or permission
logic changed. Developer rerun: 35 counted checks plus existing boundary assertions,
148 W16 assertions and build pass. Real touch/browser interaction remains untested.
An initial build command used repository root rather than web and could not find
esbuild; rerunning from web succeeded. Backend unchanged; prior 87-pass result
was not rerun for this text-only change.

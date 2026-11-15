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

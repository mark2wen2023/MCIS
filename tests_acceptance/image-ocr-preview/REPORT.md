# PNG side-by-side review — developer verification only

Parent: dc0538ade614aba99d7d6bb11152da1114f60634; same isolated candidate branch.
Recovered the original workspace after exec-server transport disconnect. Three modified
tracked files and preview.js survived; the attempted JS test file was absent. No interrupted
run was counted. Tracked patch and new JS were copied to /tmp/mcis-image-preview-recovery
before continuing. No duplicate implementation/worktree created.

Implemented in the explicit candidate app only: same-origin static preview.js; PNG canvas
view beside OCR editors; row selection draws original-pixel box and context crop. Preview
fetches existing authorized intake download with purpose, checks X-Sha256 and recorded hash,
then validates PNG header dimensions against the OCR declaration before browser decoding.
Only PNG;8192 max side/25 million pixels. Raw original files, OCR source text and saved
reviews unchanged. Clear/reload/context edit/pagehide release bitmap; generation token
prevents delayed reads/decodes from restoring cleared images. No autosave/retry or external
request. EvidencePage, PR69/97 functionality, permissions, main and PR104 unchanged.

Executed after recovery:
- `node --test service/tests/js/image-review-preview.test.cjs`:10 passed,0 skipped.
  SYNTHETIC canvas operations and decoder; not browser rendering. Covers coordinate/crop,
  ordinary format/dimension limits, release, failed decode and delayed response lifecycle.
- Extract inline script to /tmp/mcis-image-review-script.js then
  `node --check /tmp/mcis-image-review-script.js`:passed.
- `MCIS_PUBLIC_OCR_FIXTURE=/workspace/mcis-paddleocr-handoff PYTHONPATH=service
  /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q
  service/tests/test_image_review_candidate.py -rs`:15 passed in3.43s before adding the
  local-script-route test; final expanded result recorded below. These runs overlap.
- Existing public source/page-6.png passed actual PNG header size check against its manifest:
  1489x2105. Installed Pillow loaded the actual PNG successfully at1489x2105. This is not
  browser createImageBitmap, visual recognition-quality acceptance or a new OCR run.

Browser plugin absent; previously blocked browser launches were NOT retried. No Playwright,
Chrome startup, screenshots, browser console, responsive-layout or real interaction claims.
No real browser image/editor integration test. Source binding remains operator-declared;
matched dimensions/hashes do not establish correct PDF page/render association. No PDF
jump, automatic OCR, production SSO, archive restoration or production use. Initial research
contract and frozen manifest are historical; IMAGEOCRPREVIEW-impl-hashes-frozen.txt pins
this delta. No sample PNG/PDF/OCR output, database or credentials added to repository.

Final expanded candidate HTTP/parser/workflow selection: **16 passed in 3.50s**, no skip
with the public fixture available. Includes new static route/content check; not browser QA.

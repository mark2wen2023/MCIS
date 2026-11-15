# Opaque upload metadata and unparsed-step status — 2026-11-14

Independent branch from254167e; no PR61 or PR64 implementation files, report downloads,
time-alignment logic, knowledge cards, safety recommendations or dataset changes.
EvidencePage change is only an import and disclosure mount beside existing intake.

## Finding and resulting behavior

Existing intake already preserves opaque bytes with manual category declarations and
no MIME validation/media inference. A Photo-category .png may contain arbitrary bytes;
it must not be described as image decoding/recognition. The prior disclosure was mostly
in collapsed help. A same-case file-intake selection now prominently states category
is human-declared, type unverified, registration did not execute OCR/ASR/visual/audio/
video parsing, and hash equality is not content understanding/authenticity. Its path
only selects workflow help; the UI explicitly requires receipt verification for save
outcome and makes no claim about other modules' later analysis.

New-upload filenames previously allowed12 Unicode directional controls that can hide
or reorder the apparent extension. Actual old-baseline reproduction:12/12 new rejection
cases failed (server accepted). New preview/commit ingress and client request construction
reject them without rewriting or echoing the name. Normal Arabic, Chinese, emoji and
combining marks remain supported. Old metadata/binding/receipt validators remain unchanged:
old suspicious names can still be read; new replay POSTs are rejected. No new schema,
MIME assertion, parser, inline media element, model call or network operation.

## Actual tests

- `cd service && .venv/bin/pytest -q -rs tests/test_opaque_upload_metadata.py tests/test_evidence_intake_w42.py ../tests_acceptance/OPAQUE_UPLOAD_METADATA/test_independent.py`
  **117 passed,1 skipped,26.34s**. Skip is the existing .NET SDK test, unavailable here.
  New primary21 include both new ingress routes refusing all12 controls without writes,
  unknown mimeType/parsed/ocrStatus fields refused, arbitrary HTML bytes declared Photo
  remain exact opaque octet-stream with nosniff, normal Unicode preserved, historical
  binding and real receipt/read compatibility. Historical creation explicitly simulates
  the former ingress rule, not an authentic old database. Independent12 also exercise
  all directional controls and no-audit read/new-replay refusal.
- Frontend **28 primary** model/React server-render checks, **32 independent** assertions,
  plus existing **88 W4.2** assertions passed. Includes matching case/exact path, no status
  for other/unknown paths, all hash statuses never imply parsing, injection escaping,
  no media/script nodes, old/new filename validation distinction.
- Independent review found a JS `$` regex allowed trailing newline; fixed to a strict
  end assertion/type guard. Final LF/CR/CRLF and malformed-type tests pass.
- `tsc -p tsconfig.app.json --noUnusedLocals false` passed. Full `tsc -b --force` still
  fails on four unchanged unused React imports (SourceQuoteReview, ExtractionReview,
  ExtractionWorking, WorkingArchive); same errors previously reproduced on pristine
  baseline during PR61. No unrelated imports changed to suppress them.

## Browser QA and scope

Browser plugin not available. Attempted installed Playwright/Chromium with sandbox
retained; launch again fails before navigation because SUID sandbox helper configuration
is invalid. No workaround or disabled sandbox. Intended evidence-page selection flow
therefore has no real-browser click, visual, console, screenshot or mobile acceptance;
React SSR tests are explicitly separate. No browser server/deployment started here.

No full service/CI/C# pass, OCR/vision/ASR capability, production identity, authenticity,
archive-migration run, deployment or merge claim. Filename screening is not malware
scanning or complete confusable-name detection. Independent report: INDEPENDENT.md.

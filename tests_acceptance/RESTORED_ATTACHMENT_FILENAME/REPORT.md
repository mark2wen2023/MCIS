# Restored report attachment filenames — implementation verification

Independent branch from 254167e3e957784fd9d2d136a275731f33314d9b;
no PR58/intranet or semantic-support changes. User-selected scope: one concrete gap
in report attachments saved with and restored from a case.

## Gap and behavior

Existing explicitly registered file copies (including rendered report PDFs/DOCX)
retain their exact bytes and original filename in .mcase working-record archives.
Historical download nevertheless overwrote the filename/extension with .bin in both
server response and browser download code. The old baseline was actually reproduced:
`test_real_report_attachment_two_restores[pdf]` failed on the absent filename* header.

The existing historical content endpoint now rebuilds the archived intake binding
with the existing validator before exposing its name, checks request digest/identity/
source bytes, and adds percent-encoded UTF8 filename* with a fixed ASCII fallback.
UI transport validates/decodes this basename and uses it for the download; older
responses retain historical-EV-xxx.bin. Opaque content, current full authorization,
hash verification, no-store and committed Access audit remain enforced. No file is
opened/rendered by this path. UI now says download initiated, not disk save confirmed.

This does NOT automatically retain generated report-output bundles. A user still must
explicitly register a file copy. No new reportId attachment relationship, archive
version, database table, endpoint, facts, model call or source-authenticity assertion.

## Actual verification

- New backend tests12, including real PDF/DOCX renderer -> evidence intake -> .mcase
  -> new SQLite store -> download -> reexport -> second new store/download. Exact
  bytes, Unicode filename, extension, hash and inactive receipt verified.
- Combined command from service:
  `.venv/bin/pytest -q tests/test_restored_attachment_filename.py tests/test_working_record_archive.py tests/test_report_output.py -k 'not test_report_versions_full_review_gisis_and_hfacs_coexist'`
  **109 passed,1 deselected,46.24s**. Excluded existing HFACS test fails with
  HFACS_CORE_UNAVAILABLE; reproduced on the unchanged baseline (1 failed,1.23s).
- Corrupt-read metadata cases use explicitly mocked historical-row return values;
  append-only database triggers remain intact. File-byte corruption is in disposable
  fixture storage. Denied access and no-success-audit-on-corruption tested.
- Frontend new23 synthetic header/fetch checks passed, including Unicode/emoji,
  quotes/percent, traversal/control rejection, malformed UTF8, SHA mismatch,
  missing no-store and legacy filename fallback. Existing W4.2 suite88 passed.
- Actual Node frontend downloadHistory -> real loopback HTTP -> restored SQLite/blob
  returned the original DOCX bytes and Chinese basename. Only localStorage identity
  was a fixture; HTTP content was not mocked. This is not browser clicking/disk save.
- Full `tsc -b --force` fails on four existing unused React imports in SourceQuoteReview,
  ExtractionReview, ExtractionWorking, WorkingArchive; identical errors reproduced
  on baseline. `tsc -p tsconfig.app.json --noUnusedLocals false` passes (other project
  checks retained). No baseline files were changed to hide the errors.

## Browser QA limitation

Browser plugin not available. Existing installed Playwright + /usr/bin/chromium attempted
at http://127.0.0.1:15861, viewport1440x1000, against local API127.0.0.1:18861.
Intended flow: evidence page -> restored receipt/history marker -> explicit historical
attachment download -> original suggested filename and exact bytes.
Chromium launch failed before navigation: SUID sandbox helper is not configured correctly
(root ownership/mode4755 required); also emitted a crashpad database error. Sandbox was
not disabled and no protection was bypassed. No page identity/DOM/overlay/console/
screenshot/click/mobile/browser-save acceptance is claimed. Local servers were test-only,
not deployment. Backend and actual frontend transport checks above are separate evidence.

No full service suite, C# acceptance, CI, production identity, deployment or merge claim.

## Independent acceptance

Separate reviewer found no blocking defect:20 Python tests/0 skipped plus14 frontend
assertions passed; root reran20/20 and14 after review. See INDEPENDENT.md. These are
additional synthetic boundary checks, not independent browser/live HTTP acceptance.
Frozen implementation is ready for coordinator review; two loopback test servers stopped.

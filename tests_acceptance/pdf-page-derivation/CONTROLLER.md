# PDF derived-page controller branch (not a mounted host)

Parent: `03e97b65ab61e9b5415d2f050ceaf28a97c80f5f`. This changes the actual `service/mcis_service/image_review/preview.js` controller, its existing page control guards, and its existing Node test suite. No new page, server route, permission, persistence or verified-status flag.

## Trusted caller interface

The controller now has `loadDerived(bytes, description)`, separate from unchanged `load(read, expected)` for registered originals. The description has exactly the output fields of the local PDF renderer: sourceSha256, physicalPage, renderSpec, pageSha256, width, height. Only the renderer's PNG / 72dpi / scaleTo256 / MediaBox profile, 1–8 physical pages, dimensions ≤256 and bytes ≤1MiB are accepted. It copies both bytes and description, verifies PNG header/dimensions and actual SHA256 with WebCrypto, then uses the existing decoder and canvas path. It labels the view “PDF派生页”, physical page, original PDF digest and derived PNG digest; selection is a declared region of derived pixels, not an OCR line or registered original. These checks do not prove provenance/authenticity or grant access: the caller must be trusted and must already have received authorized source bytes.

`create` accepts a `controls` callback returning `{originalRead: [...buttons], ocrReview: [...buttons]}`. Derived mode requires this explicit interface, disables supplied controls, and provides `assertOriginalAction()` for handler guards. Errors erase pixels, remain in derived mode and keep actions blocked; no fallback read. `clear()` invalidates outstanding work, closes decoded bitmap and restores each supplied control's prior disabled state. An intentional original-context load after clearing uses the existing path. The surrounding host still owns its case/source/version lifecycle and must call `clear` when invalidated. This is not a new authorization mechanism.

The existing HTML supplies its original load/download and OCR-save controls and guards their handlers, including guarding **before** original `load` clears state. No HTML caller invokes `loadDerived`: a trusted Python-to-JS host/transport is still absent. No original or OCR run is fabricated, no HTTP endpoint is added. Consequently the actual page's source panel/line model has not been adapted or browser-validated for a host-delivered derived context; do not mount one by calling this API without completing that host boundary. The new branch is a reusable controller seam, not completed UI integration.

## Exact offline checks

```sh
node --check service/mcis_service/image_review/preview.js
node --test service/tests/js/image-review-preview.test.cjs
```

All original 10 checks plus 6 new checks pass. The new checks cover derived labels/selection, copied description, disable/restore state, handler guard, digest/page/spec/dimensions rejection, explicit controls required, late decode after clear, and an old original read completing after the derived view. The HTML wiring check is a source assertion. The suite uses its existing synthetic canvas/decoder and header-only PNG fixture; these are not real PNG decoding, browser rendering, accessibility or host authorization tests. WebCrypto SHA256 executes normally. The preceding PDF candidate separately exercised genuine Poppler/Pillow and remains unchanged; that run is not repeated or counted here.

No model/OCR, services, real/third-party documents, archive, report, generated data or remote workflow is involved.

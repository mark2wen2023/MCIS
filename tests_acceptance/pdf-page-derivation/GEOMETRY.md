# W4 asymmetric same-page coordinate check

Parent b64b8ae0ce70ee7923819b777c1e79be4eb61bf6. Three new test-side files;
existing fixture, renderer, controller and helper remain byte-for-byte unchanged.
The new integration follows check.py's actual registration/read/audit sequence
in a fresh SQLite database, substituting only synthetic PDF artwork and the
post-read coordinate assertions. No production behavior is substituted.

```sh
/path/to/existing/venv/bin/python -I -B tests_acceptance/pdf-page-derivation/check_geometry.py
node --check tests_acceptance/pdf-page-derivation/geometry_consumer.cjs
```

Requires existing SQLAlchemy/Pillow, Poppler pdfinfo/pdftoppm, Node and the same
fixed local Git objects as check.py. GIT_NO_LAZY_FETCH=1; no downloads/fallback.
Pins verify original helper, derive.py and production preview.js.

Independent drawing expectations: white PDF MediaBox [0 0 256 160]; green A
rectangle [48,108,18,12], magenta B [148,45,18,12] in PDF bottom-left coordinates.
At the existing scale 256, decoded PNG is 256x160, top-left pixel coordinates.

* Exact A crop [40,32,92,68], 52x36: pixel (16,14) green, contains green/no magenta.
* Same-page/same-bytes shifted crop [140,95,192,131], 52x36: (16,14) magenta,
  contains magenta/no green. This is a valid crop of another mark, NOT an access denial.
* Transposed [32,40,68,92] is in bounds but its (16,14) does not match green A.
* Context crop [28,20,104,80], 76x60: green/no magenta; separately cropped and
  decoded by Pillow. Exact and context crop are distinct, not interchangeable.
* Production controller receives the very same derived PNG via ephemeral stdin.
  Canvas spy checks strokeRect(40,32,52,36), page drawImage(bitmap,0,0), and
  crop drawImage(bitmap,28,20,76,60,0,0,76,60): exactly 12 pixels each side.

Observed: one integrated test passed. Genuine preview/commit/download use the
existing synthetic Ctx and default policy, with one Register + one Access,
2 custody rows, 2 audit rows, verified chains. Geometry/canvas checks add no
reads or writes; original file and counts remain unchanged. Existing wrong-page,
changed-byte and out-of-document checks remain. No original PDF/DB persisted.

Real: SQLite, registered byte read, audits, Poppler rasterization, Pillow pixels,
production controller calculations. Synthetic boundary: caller identity/context,
canvas/bitmap decoder spy. No HTTP, actual browser, OCR, product host or approval
of evidence meaning. No report, permission, original processing or UI changes.

# Supplied image/PDF byte consistency — isolated research

Base79f90511d2efbaf5c2d10d92ef25ece2120c563f; branch research/image-pdf-byte-consistency. No product route, permission, archive allowlist, exporter or restoration change.

## Implementation and boundary

`image_bytes.check_image_members(index,payloads)` applies the existing offline member/association checks, then examines supplied PDF/PNG bytes only. Registered/current/member SHA256 declarations must agree with the bytes. It uses existing installed Pillow13.0.0 for complete single-frame PNG verify/decode and actual dimensions; this bounded profile allows at most10000 per dimension and20million pixels. It uses installed Poppler pdfinfo26.05.0 on PDF bytes via stdin (no shell/network or package-provided path), with a10second timeout and a minimal environment. Missing dependency, nonzero exit, diagnostic stderr, unavailable/unsupported page count or mismatch rejects; no automatic install/fallback. PDFs outside1–2000pages or not supported by this inspection profile reject. No claim of hostile-document isolation or production resource validation is made.

Each image's declared PDF page must be within the actual reported page count; its declared dimensions must match PNG decoding. This checks page-number bounds **only**. It does NOT prove the image was rendered from that PDF page, verify printed page numbering, render the PDF, or authenticate originals. page_mapping_verified remains false. PNG is generated independently in the tests deliberately; it is not represented as a verified PDF rendering.

`image_line_contract.py` is an isolated research snapshot of image candidate91962113bd98778d3538f0e8e9879a014023c21f's line contract; only the dependency import is replaced with the same text-validation helper and digest regex. It is not a merge of the image application or an alternative production route. Line count/identity, pending/confirmed markers, scores, boxes, polygons, null recognizer page index and unsupported table behavior are retained. The new checker compares every candidate text/score/box/polygon against the retained PP-OCR arrays, independently matches recognizer metadata and source declarations, and preserves full raw JSON. Human review remains a declaration, never proof of facts. Historical task execution remains forbidden by the outer research contract.

Successful output still has restore_ready=false, export_allowed=false, authorization_verified=false, authenticity_verified=false, ocr_execution_verified=false. Source_bytes_match refers only to the supplied bytes/declarations; no product source files, active receipts or private evidence were read. The remaining native inventory→members adapter, full original custody semantics, cross-file/database snapshot, publication and recovery barriers are not implemented.

## Exact developer test selection

Only the12 new nodes in `image-byte-nodeids.txt` were run, explicitly supplied as individual command arguments. No full file/directory selection, pytest collection-only run, preflight file, whole repository, write-refusal/security probe, or paused node was executed. In particular `test_native_two_revisions_inventory_is_read_only` was NOT selected. Imported `test_contract.fixture` is a fixture builder only, not a call to its tests.

Command prefix at repository root:
```
PYTHONPATH=. /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q --rootdir=/workspace/mcis-sensevoice-review
```
Followed by the12 exact nodeids in the adjacent list, then `--tb=short` (no other selection arguments).

Result: **12 passed in0.40s**, no failures/skips. This is developer-only, not independent acceptance; not added to prior83/57 totals. Actual in-memory PDF/PNG parsing used installed software; PDF generation used ReportLab5.1.0. No model, real report sample or browser exercised. One node simulates an unavailable inspector by returning None from the executable lookup; it does not attempt a denied operation or change environment settings.

Generated assets and fabricated OCR remain in memory; no PDFs, PNGs, models, databases or credentials are deliverables. Tests cover ordinary success, out-of-range page, wrong declared dimensions, missing result, inconsistent digest, divergent candidate text, metadata mismatch, retained null/blank semantics, box bounds, unavailable dependency, unsupported tables and false page-verification claims. No software installed/downloaded, originals overwritten, real model called, PR body edited, merge or deployment performed.

# Synthetic registered PDF → physical page → crop

Test-only adapter, parent `900a8e58585693a408706129ba9562d159ed5eb9`.
Unmodified official registration/read modules are from `91962113bd98778d3538f0e8e9879a014023c21f`.
No production route, authorization, schema, archive, OCR, state flag or UI changes.

## Run

```sh
/path/to/existing/venv/bin/python -I -B tests_acceptance/pdf-page-derivation/check.py
```

Existing dependencies only: Python, SQLAlchemy/FastAPI/jsonschema and their dependencies, Pillow, `pdfinfo` and `pdftoppm` on PATH. Linux developer environment used `/workspace/mcis/service/.venv/bin/python`, Pillow 13.0.0, Poppler 26.05.0. No installation/download or service startup. Keep the venv executable's lexical path.

The immutable helper `tests_acceptance/image-reopen-source/check.py` is checked against parent Git bytes and SHA256 `76de411135b4754ec99ca2c6e8c9740609b13205a7915397e2d2ac15023a9b60`. Its allowlist materializes fixed source files and contracts only and verifies Git blob hashes. Fixed objects must already be local; `GIT_NO_LAZY_FETCH=1`, no network fallback. No main application, seeds, model registry, default database or unrelated test collection. The helper's old image test is **not** run.

## Actual path and new evidence

A fresh temporary SQLite database contains only `SYN-XREPO-001`, with explicit synthetic case/policy prerequisites and context. The unchanged `preview_input` / `commit_input` handlers register generated valid PDF bytes; `download` performs existing role/policy/container checks and commits one Access. No authorization logic is replaced. Request body and investigator context are explicitly synthetic, not a login test. Original files are never changed.

The generated PDF has two physical 72pt-square pages, first red and second blue, with a valid catalog/page tree/content streams/xref/trailer; no text, fonts, OCR or external resources. Real Poppler parses and renders it. This is distinct from the previous opaque PDF prerequisite and PNG-reopen test.

`derive.render` accepts already-read bytes and the registered expected raw SHA, checks equality before Poppler, uses stdin and a private temporary output directory, and returns:

- source SHA256 and one-based **physical** page (not printed page);
- fixed PNG / 72 dpi / scale-to-256 / MediaBox rendering specification;
- derived page PNG SHA256 and actual dimensions, plus PNG bytes for the local caller.

Profile bounds: PDF ≤2 MiB, 1–8 physical pages, selected page in range, unencrypted, each tool ≤15 seconds, output PNG ≤1 MiB and dimensions ≤256 each. No caller-supplied executable, path or rendering flags. Tool failure/diagnostics reject. These are engineering limits for this synthetic exercise, **not** a hostile-document sandbox or total CPU/memory guarantee. Tool versions are observed, not pinned by a package manager; byte-level PNG output can differ across versions.

`derive.crop` checks independent expected source SHA/page, page PNG SHA and render specification before accepting an integer top-left pixel rectangle. It returns parent page digest, rectangle/coordinate space and crop digest plus crop bytes. A host-generated provenance record is not a capability or authenticity proof; an arbitrary forged record is outside this local trust boundary. Nothing is persisted as an approved mapping or registered derivative.

## Executed checks

One integrated test, ordinary positive plus three negative controls:

1. Official register/read bytes and returned SHA match; one Register + one Access, two custody and two audit rows.
2. Both physical pages render as 256×256; page digests differ. Each 64×64 crop decodes to its independently expected red/blue center pixel and carries the corresponding source/page/digest/box.
3. Page 2 image/record presented for expected page 1 rejects.
4. Changed input bytes with the old registered SHA reject before rendering.
5. Physical page 3 rejects against the actual two-page document.
6. After all renders/negatives, table counts remain unchanged, original file bytes still match, and custody/audit chains verify. No second original read or Access.

Developer Linux run: 1 integrated test passed, exit 0 (0.254s before packaging). No model, browser, HTTP, report or archive execution. No raw PDF/PNG/crop, database, credentials or output receipt is committed.

## Remaining product boundary

This closes the local synthetic derivation segment only. It does not mount a PDF viewer, persist/reopen derived provenance, validate human meaning, mark `pageMappingVerified`, or provide an approved production renderer/identity. Such product integration must retain server-owned registration binding and independently decide renderer isolation, artifact lifetime and display behavior. Existing OCR candidate remains unchanged and unverified.

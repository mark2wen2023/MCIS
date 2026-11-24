# Registered image fragment after database reopen

Source and parent: `91962113bd98778d3538f0e8e9879a014023c21f` (`candidate/image-ocr-review`). Remote main inspected at `94d5e38c926fda232bb987b60fa9145e4bcf01a7`; main has opaque evidence registration, not this image-review module. This candidate adds only this runbook and the acceptance script, not product code or a new UI.

## Independent command

From any clean checkout containing this script and the pinned source object, use an existing Python environment with SQLAlchemy, FastAPI, jsonschema and their installed dependencies:

```sh
/path/to/existing/venv/bin/python -I -B tests_acceptance/image-reopen-source/check.py
```

Linux developer command used `/workspace/mcis/service/.venv/bin/python`. Keep the venv executable path; do not resolve its symlink to the base interpreter. No dependencies are installed. Git must already contain the source commit and the exact paths enumerated in `PATHS`. Missing objects fail; `GIT_NO_LAZY_FETCH=1` prevents lazy fetch. The reader uses only pinned `git ls-tree`/`git show` paths and verifies each Git blob hash. No default application, model registry, seed, full test collection, environment configuration, user database, HTTP listener, browser, OCR runtime or external material is loaded. Only those source modules are materialized into a disposable directory; a post-run module-origin check enforces the same list. This is not a sandbox/security-isolation claim.

## New observation versus existing tests

`service/tests/test_image_review_candidate.py:test_roundtrip_review_restart_download_and_archive_refusal` downloads placeholder bytes **before** reopening, then checks revision text after reopening. It also imports `main` and broader test configuration. This narrower direct-handler check instead proves that **after a new Database/engine/session** the saved line still locates the same registered PNG and the authorized original-return handler delivers those exact bytes. It does not import that broader suite or execute its archive calls.

The test creates only `SYN-XREPO-001` in fresh temporary SQLite, using explicit synthetic case/policy prerequisites. Registration, review rows, source revalidation and Access are produced by the unchanged official handlers:

- `evidence_intake.router.preview_input` / `commit_input`;
- `image_review.app.register` / `review` / `read`;
- `evidence_intake.router.download`, including unchanged role/policy, container protection and Access transaction.

Only request-body transport and initial `Ctx` are fixtures. `Ctx('Investigator', ...)` is explicitly synthetic, not authentication or real-account proof. Existing policy is unmodified. Audit/custody and image-history append-only triggers are installed in the temporary schema as in their existing initialization. No report or binding tables are initialized or written.

## Assertions and bounds

One integrated test, with both normal and missing-run branches:

1. Four opaque prerequisite files are normally registered; returned raw SHA values match input bytes. The image is an actual generated 2×1 PNG (red and blue pixels). OCR output/text is fabricated; no recognizer executes. PDF prerequisite is explicitly **opaque placeholder bytes, not a valid PDF**, so there is no PDF rendering/decoding or verified page-to-image lineage claim.
2. One synthetic transcription correction is saved through the existing review handler. After disposing the old engine and opening a new one, revision 1 and both immutable history rows remain; original line text, index, box, polygon, registration IDs/digests and source hashes are unchanged. `raw_page_index` remains null. Page declaration is not proof.
3. Source revalidation on reopening records zero Access. Unknown run returns 404 and changes neither custody, audit nor review counts. This is an ordinary missing-record test, not a security probe or cross-case permission test.
4. Explicit original return **after** reopen yields identical PNG bytes, raw SHA header, actual 2×1 dimensions and red/blue scanline. The existing response MIME is `application/octet-stream`, not a newly inferred image MIME.
5. Exactly one Access references the same image evidence ID/hash; audit grows by one, both chains verify, saved review history remains identical after another read. `factVerified`, `pageMappingVerified`, `originalAuthenticityVerified` and `archiveSupported` stay false.

Developer Linux result: **1 test passed**, exit 0 (0.241s test time before packaging). Early development attempts exited nonzero for a missing synthetic case `accidentType`, then a missing allowlisted `track_history` dependency; both prerequisites were corrected without changing production code or bypassing its checks.

This is database connection reopen, not a separate process crash/restart or archive restore. The PNG box is a retained declared locator; it does not establish the text's visual accuracy or facts. No real UI fragment click, browser, true PDF page rendering, model, real login, cross-repository flow or full-case closure is verified. No generated files, SQLite, receipt, image or OCR output is committed.

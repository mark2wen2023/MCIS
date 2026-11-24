# W4 bounded synthetic PDF host candidate

Base: 079c3eff5ed9859d1cdd17c83035ab7dac2857cd.
Default off; no publication, CI, real documents, OCR or model invocation.

## Enable only in the existing explicitly configured image-review application
The host may pass `synthetic_pdf_binding=SyntheticPdfBinding(run_id, revision,
registration_digest, evidence_id)` to `create_image_review_app`. These values must
come from its already registered single synthetic review run, never a request.
Only SYN-XREPO-001 and the existing 674-byte synthetic PDF SHA256
92cf698d3070092139444f94b7dacb7286f774b6186503917e534b253734e774
are supported; the server always selects physical page 1.
The original download route is unchanged. The optional binding is process memory,
not a new credential or an authentication system. Existing local role headers
retain their known authentication limitation.

The added POST accepts only expectedRevision. It reuses intake authorization,
load_receipt, container protection and the original Access append transaction.
Poppler/Pillow rendering happens under the existing SQLite policy/read lock.
The response is delivered only after audit commit, containing PNG base64,
case/run/revision and the existing derivation description. It contains neither
PDF bytes nor registration tokens. The pinned existing derive.py remains in its
acceptance location and is SHA-checked before loading; this is an explicitly
synthetic candidate, not a general PDF service.

The HTML's new button is hidden unless the server has an explicit binding.
A separate host generation invalidates delayed HTTP responses, even A→B→A.
The actual existing preview controller is reused unchanged. OCR rows are hidden,
selection cleared and retained line callbacks guarded in derived mode; no OCR
coordinates are applied. Clearing restores the original PNG workflow.

## Reproduce in a checkout of the base with this patch applied
Use existing installed Python dependencies (FastAPI, SQLAlchemy, httpx, Pillow),
Poppler pdfinfo/pdftoppm, Node, and optional installed happy-dom; no install.
Keep your Python virtual environment lexical path.

```sh
/path/to/existing/venv/bin/python -I -B tests_acceptance/pdf-page-derivation/check_host.py
node --test service/tests/js/image-review-preview.test.cjs
MCIS_HAPPY_DOM=/absolute/path/to/existing/happy-dom/lib/index.js node --test tests_acceptance/pdf-page-derivation/check_ui.cjs
```

Linux results: 14 server tests, 16 controller tests (one HTML source guard updated), 14 HTML-host tests;
each command exit 0. Initial test setup used a wrong registration URL and expected
201 instead of the existing 200; corrected only the test, then all passed.

Server tests use real FastAPI ASGI routing/TestClient, actual registration handlers,
temporary on-disk SQLite, real policy and audit code, and real Poppler/Pillow.
Only the case/policy and existing review row are synthetic test setup.
No OCR run is fabricated: the review row is explicitly seeded, not created by an
OCR import or claimed production workflow. Each test deletes its temporary files.
The audit-failure negative uses a temporary SQLite INSERT trigger, not an
authorization bypass. Success checks a new connection, both audit chains, exactly
one Access, unchanged original bytes, no additional Evidence or review rows.
Negatives cover default off, wrong case/run, lost permission, unauthorized role,
stale request/current revision, wrong digest/page, client source/page selection,
changed original bytes, and audit failure.

HTML tests execute the actual inline page script and unchanged preview controller
with happy-dom; canvas, bitmap decoder and HTTP responses are labelled synthetic
controls. Header-only PNG controls are NOT real PNG decode. Server test separately
decodes actual rendered PNG via Pillow. Not a browser/pixel/accessibility claim.
No full create_app startup, production session, remote revocation delivery, OCR
service or deployment has been tested. Existing normal Chromium sandbox launch
is blocked; it was not retried or bypassed.

## Delivery
Only seven code/test files plus this note change. No dependency copies belong in
the patch. The local Git database lacks the base commit object; therefore this is
a patch against exact exported base blobs, not a fabricated local Git commit.
Apply with `git apply --check candidate.patch`, then `git apply candidate.patch`
on a clean isolated checkout at the base. Coordinator performs independent review
and any eventual commit/push.

## Context invalidation correction
Input changes revoke the loaded-context generation, clear state/context and remove
old source/line nodes. Captured download/save/locate callbacks carry their original
generation and refuse before any request, including after A-B-A or rereading the
same run. Pending original reads are checked again before delivery. Unsaved edits
are explicitly discarded on context change; no writable old draft is retained.
A PDF failure also revokes the loaded context. Explicit clear within an unchanged
active context only clears preview and still permits the normal PNG workflow.
Four added HTML regression cases cover both input controls, same-context clear,
and revision reread; failures/late responses remain covered. No backend changes
in this correction; prior 14 server results are unchanged, not rerun here.

The existing HTML source-guard assertion was updated to require the new context-token guard before the retained original-mode guard; its first run correctly failed on the changed function signature. No behavioral test was removed.

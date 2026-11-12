# W4.2 implementation checks

Run `bash web/tests/run-evidence-intake-w42.sh` from the repository root: 88 model/API/static-render assertions. These are not browser interaction tests.

Real-backend smoke:

```sh
MCIS_BROWSER_BIN=/path/to/already-installed/chromium python web/tests/evidence-intake-w42.browser.py
```

Uses existing global Python Playwright, project `service/.venv`, Node dependencies and an existing Chromium. No dependencies are installed. The script starts service on 127.0.0.1:18840 and Vite on 127.0.0.1:15840, runs the actual browser in the same process tree, then stops the services. The fixture contains only synthetic cases and files in a fresh temporary database. It does not mock successful API responses or upload actual investigation materials. The connected browser could not reach execution-environment localhost, so the previously authorized existing-Playwright fallback is used.

Flow: evidence page → choose local opaque bytes → server preview → human Restricted confirmation → register → actual list/custody → purpose-bearing download → reopen receipt. Initial smoke result: 17 checks passed, including zero-byte registration, raw binary bytes, extraction/registration separation, double-click one POST, preview zero evidence/custody writes, invalidation on edited metadata, download Access purpose preservation, receipt reads adding no Access, 1440/1920 width and no JavaScript runtime error. Local screenshots/results are under `logs/w42-browser-self`; do not treat screenshots as published artifacts.

TypeScript, dedicated-module lint and build passed. The existing bundle-size warning remains. A first harness syntax typo and a textarea exact-label selector were corrected before the final run; the final UI also gives textareas explicit accessible names.

This is implementation smoke, not independent acceptance. Fault rollback, malicious-path/permission/storage-corruption cases, response-loss recovery and delayed response navigation/role/selection races require the separate independent suite. No mobile or exhaustive accessibility certification, original-source authenticity, OCR/ASR/VDR decoding, clock calibration, production authentication or deployment is claimed.

## D01 implementation repair

Independent acceptance found that closing during a dispatched commit could abort its transport before the server read the body. Only the exact commit POST now detaches from the resettable read AbortSignal. Preview/receipt reads remain abortable; download retains its previous semantics. Generation/identity guards still suppress late UI responses, and there is no automatic retry or keepalive. A signal already aborted before dispatch rejects without sending.

Self verification after repair: 88 assertions (original 81 plus 7 signal/transport checks), TypeScript/dedicated lint/build pass; 20 actual-backend browser checks (original 17 plus 3 delayed-body D01 regressions) pass. The synthetic middleware delays reading the commit body for one second; Close/reopen does not abort the already-dispatched commit, its late response cannot populate the new form, and exactly one Register exists. No independent acceptance assertions or backend implementation were changed.

Closing cannot undo a registration already accepted by the service; an in-flight result still requires later lookup. Browser/page termination or network failure can leave the outcome unknown. This is not a guarantee that every dispatched request completes.

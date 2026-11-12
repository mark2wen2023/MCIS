# W4.2 existing-file copy intake verification

## Scope and professional boundary

Baseline main `096e3d2e7f941b4878a19c7376aa2255261350ca`, tree `5324c359cbb36ef70070e11f29b4e8767ccb51af` (including W10.2 and W8.4). The original evidence-centre design and NIST IR8387 / SWGDE acquisition documentation / IMO recommended practice informed the limited contract in `contracts/W4.2-evidence-intake.md`.

Delivered: one already-obtained opaque file copy, known extractor and known UTC whole-second extraction time, human source/acquisition declaration, Restricted confirmation, actual zero-write server preview, first registration, verified receipt recovery, and purpose-bearing original download that records Access/audit. Original bytes are not decoded or executed. Registration UTC is distinct from declared extraction UTC. Unknown or subsecond extraction times are not replaced with now, file metadata or guesses; supporting those requires a later C#/package contract. The 8MiB file / 12MiB request cap is this slice's engineering budget, not a maritime evidential-validity threshold.

Original bytes use generated exclusive paths. Evidence snapshot, Register and audit share one database transaction, with ordinary failure cleanup and same-request idempotency. Register.detail retains versioned request metadata; existing package format includes the indexed original and custody line without a new table or package extension. Full Restricted reads reject Redacted access levels and obey field restrictions. Existing legacy routes are not represented as fully repaired.

## Verification on the final implementation

- Full `service/tests`: **908 passed in 254.86 s**, no failures or skips. The final backend was unchanged throughout; the frontend-only D01 fix was separately rechecked below. Includes 85 new implementation tests and existing contract/core/legacy suites. Source-built existing C# core/compatibility tools used; no software installation.
- Frontend: **1,313 assertions**, TypeScript/build passed. Source lint exits 0 with existing 12 warnings; dedicated new module lint passes. Existing bundle-size warning remains.
- Independent W4.2: **71 in-process API tests** (not network HTTP), **1 actual HTTP combination** (five endpoint families, same/different request concurrency, fresh-database `.mcase` roundtrip), **6 actual Chromium groups**. All pass. All 13 frozen hashes match before and after final independent acceptance.
- Independent D01/A01 found and closed: closing the panel aborted a commit whose body the delayed test server had not yet consumed. This was not rollback of committed data. The commit request no longer shares the cancellable read signal; old UI results remain invalidated. Original red assertion and v1 freeze remain. Browser/whole-page termination or network loss can still leave an unknown outcome; no keepalive guarantee is claimed.
- Browser coverage includes actual binary and empty bytes, no upload on local selection, zero-write preview, metadata invalidation, human confirmation, duplicate-click gate, literal XSS text, original byte download, read-only receipt reopening, lost-response recovery, case/identity/Back/session/selected-evidence late-response isolation, delayed in-flight commit after closing, and actual 8MiB save/download with +1 byte local rejection. Desktop 1440/1920 reviewed. Keyboard coverage is limited, not a full accessibility certification.
- Implementation Chromium smoke: **20 checks**, preserving original 17 plus delayed-body D01 regressions.
- Affected existing W10.2 independent suite rerun: **45/45**; its 12 implementation freezes remain unchanged. Existing W8.4 actual-backend browser: **39**, plus three legacy empty/whitespace-title checks, all pass. These regressions are separate from the new W4.2 independent numbers.

## Preservation, reproduction and remaining limits

New implementation is isolated under evidence_intake/evidenceIntake plus dedicated style. EvidencePage only embeds the panel, refreshes/selects actual registrations and adds keyboard-capable evidence selection. Shared main.py has two registration lines; OpenAPI adds five schemas and five paths. Removing those exact additions reproduces the previous main files byte-for-byte. No W10, W8.4, ECFC, old evidence route, common clock, schema, package or report source implementation changed. W11 was not yet published and is not included or retested here.

Run the independent commands in `tests_acceptance/W42/README.md`. All fixtures are synthetic, temporary databases, loopback-only real backend/Vite/browser in one process tree. Existing Playwright fallback was used because the connected browser cannot reach this execution environment's localhost. No real incident files, OCR/ASR/model calls, installation, deployment or branch-protection changes.

Do not infer source authenticity, real-world complete chain of custody, legal confidentiality classification, whole W4 completion, multimedia playback, device-clock calibration, production authentication, multiworker concurrency, filesystem/SQLite crash atomicity, all mobile layouts or comprehensive accessibility from these results. Legacy package import and other old-interface limitations remain.

Published artifacts are explicit source tests, compact final/red results, review/defect history and freezes. Environment logs, screenshots, temporary databases, generated binaries and dependency/cache files remain local and are not published.

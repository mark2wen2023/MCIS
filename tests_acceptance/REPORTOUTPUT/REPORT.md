# Report output A — independent acceptance

## Verdict

**PASS within the tested scope below.** Frozen implementation: 20 files, SHA256 checked before and after final API/DB and real-browser runs, and again after the final PDF text-extraction enhancement. Exact hashes are in `verified-impl-sha256.txt`. No production files were changed by this acceptance work.

- Independent API/DB suite: **49 passed, 11.56 seconds** on final test bytes.
- Real owned-service Chromium scenario: **passed** on the same frozen implementation, with two real renderer downloads, two explicitly faulted deliveries after real commits, and one delayed real response discarded after identity change.
- Browser-side validator: one valid actual downloaded PDF bundle accepted; **eight independent mutations rejected** (four binary header/CRC/directory changes, trailing bytes, wrong rendering language, wrong actor, wrong preview digest).
- Only synthetic data, empty seed-disabled databases and loopback processes. No external model, real report, deployment or production identity assertion.

## Independently exercised

Real PDF and DOCX each render exactly once. PDF text is extracted with `pdftotext` and contains the synthetic report/case IDs and draft status; DOCX XML contains the report ID. Stored bilingual report remains byte-equivalent under canonical JSON while rendering English. Four members, member byte lengths/SHA values, original persisted audit line and snapshot, reason-bound input/output SHA values and one new audit event are checked. Ordinary old PDF/DOCX exports still work with unchanged empty reason semantics.

All 12 policy category denials refuse both existing and missing report requests before rendering; default Investigator and an applicable field rule refuse. All categories ReadOnly allow export. Wrong stored report case identity and wrong source row/document identity refuse. Unrelated current interview source missing/hash mismatch refuses both before rendering and when introduced during rendering.

During renderer execution an actual second-thread/second-connection transaction commits report, allowed policy or denied policy changes. Result is 409 or 403 and no export audit, demonstrating the renderer is outside the writer transaction in these controlled interleavings. This is not a production multiworker load proof. A deliberately mutating renderer cannot change captured report.json or the persisted report.

Injected renderer, ZIP assembly and final commit failures leave every SQLite table unchanged. A separately injected response construction failure after commit returns controlled500/no-store and retains exactly one export audit. New export reason survives actual `.mcase` export and restricted restore to a fresh database; generated rendition bytes are not restored as a server original.

Actual boundaries: 1025 request bytes reject; canonical report exactly2MiB accepts preview and2MiB+1 rejects; synthetic rendered output exactly16MiB accepts and16MiB+1 rejects. The 16MiB test uses a byte-size stub, not a real valid oversized DOCX. Separately lowering each of the five engineering limits verifies rejection/rollback paths; this is **not** a claim that actual256KiB audit,16KiB manifest or19MiB ZIP boundaries were all reached. Duplicate JSON keys, BOM, NaN, lone surrogate and missing required fields reject without audit.

## Real browser and delivery semantics

The script owns a new loopback service using an inherited bound socket and a temporary empty database. It drives the actual report page and explicit preview/acknowledgment. PDF and DOCX downloads are opened as ZIPs and their actual member hashes checked.

For fault testing only, Playwright first executes each genuine POST, receives real200, then substitutes503 or malformed ZIP delivery. UI remains unknown across reload, does not automatically POST again, and requires explicit abandonment. A fifth real successful POST response is held until identity switches to Investigator; it is discarded without download and the protected report is cleared by actual403. SQLite finally contains exactly five export audits. These cases are transport fault injection, not a claim the backend naturally emitted malformed ZIP or503.

No audit-count recovery is used by the product UI. Successful save invocation is not durable physical-file-storage proof. Role/operator are local self-declarations, hashes are unsigned consistency checks, and the ZIP is client-retained only.

## Observations and limits

No confirmed unresolved product defect was found in this independent scope. During mutable development the first browser download attempt timed out; its cause was not isolated, so it is not counted as a proved defect/fix. Subsequent development and final frozen runs succeeded. A test initially awaited an incorrect403 wording; it was corrected to the actual report-page message, not by weakening the no-download assertion. Expected403 console messages are retained locally. Pytest emits a pre-existing Starlette/httpx deprecation warning.

Independent tests do not exhaust all strict JSON/ZIP/audit-field mutations, all field-rule methods, all malformed policy shapes, all source confidentiality combinations, every charset spelling, concurrent multiprocess export or every browser navigation schedule. The implementation team's additional tests are not counted as independent results. Browser identity switching is real; there is no separate final real-browser case-switch/unmount interleaving here. No full visual pagination/accessibility review, authentication, signature, expert review, LLM or full evidence-closure verification is claimed.

## Reproduce

From repository root with prepared dependencies and `pdftotext`:

```
PYTHONPATH=service service/.venv/bin/pytest -q tests_acceptance/REPORTOUTPUT/test_bundle.py
MCIS_BROWSER_BIN=<existing-headless-chromium> python tests_acceptance/REPORTOUTPUT/browser_real.py
sha256sum -c tests_acceptance/REPORTOUTPUT/verified-impl-sha256.txt
```

Public acceptance files: `test_bundle.py`, `server.py`, `browser_real.py`, this report, `verified-impl-sha256.txt`, and `DEFECTS/REPORTOUTPUT.md`. Exclude `local-*` logs, caches and development-only plan from acceptance publication.

# Independent review: internal digital PDF text extraction

Final `derive.py` SHA256: `b1aadeda1f9aefff8c8acce631e849e431bf7e6045496b5d025b03eba13d2bfc`.

## Result

`cd pdf-text-candidate && ../mcis-work/service/.venv/bin/python -m pytest -q`

**24 passed in 2.62 seconds**, consisting of 10 author and 14 independent cases. Independent tests check immutable input, invalid time budgets, combined stdout/stderr exact budget and one-byte overrun, nonzero parser exit despite partial stdout, same-process-group descendant cleanup, invalid UTF-8, warnings, and second-page failure returning no partial artifact. Author public-artifact test also ran: fixed source PDF SHA, 53 physical pages, source unchanged, concatenated extraction equals existing layout text, per-page SHA checks.

## Defect found and corrected

Initial implementation killed the process group only if its leader was still running. Independent subprocess test demonstrated a leader exiting while a descendant retained its pipes; after deadline the descendant was still alive. The test cleaned up that synthetic child. Author changed finally to attempt group kill regardless of leader state, ignoring an already-absent group, then wait for the leader. Final regression passed.

Independent test allows up to 300ms for SIGKILL scheduling and treats /proc missing/process-gone or zombie as terminated. A post-fix check initially raced with /proc disappearance; the test was corrected to handle ProcessLookupError/FileNotFoundError. This is not a removed assertion or skipped failure. Child still alive after this bounded wait fails the test.

## Limits

Acceptable as an isolated internal candidate, **not production ingestion approval**. No OCR, image understanding, real-model call, factual/completeness validation, API, authorization, production store, CI, remote change or deployment. Physical PDF pages are not printed page numbers. A text-bearing page can still contain unextracted images. SHA binds caller bytes, not document authenticity.

Process output/wall-time controls are not a CPU/memory/security sandbox. Tests cover descendants remaining in the newly created process group, not descendants escaping into another session. Executable identity trusts local PATH. Unusual executable/version-output failures may surface as native exceptions rather than DerivationError; these still abort without artifact and are not certified HTTP error semantics. Production hostile-input handling needs a separately hardened parser boundary and normalized operational errors.

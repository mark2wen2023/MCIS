# Independent local worksheet restore review — 2026-11-14

A separate native reviewer inspected the frozen restore generator/import script and executed both actual generated-page scripts in a separate minimal DOM/File/download adapter. No implementation or frozen file was changed. All new review files stay within research/semantic_support.

Result: **23 independent tests passed; combined related suite 122/122 passed, zero skips. All five restore frozen hashes match. No blocking defect found in the tested scope.**

```sh
service/.venv/bin/pytest -q research/semantic_support/test_browser_import*.py research/semantic_support/test_browser_review.py research/semantic_support/test_evaluate*.py research/semantic_support/test_render_review*.py research/semantic_support/test_export_review*.py tests_acceptance/SEMANTIC_BROWSER_EXPORT/test_independent.py
```

Independent coverage:

- Eighteen hostile/invalid documents: invalid UTF-8, BOM, trailing JSON, exponent-spelled version, duplicate root keys, escaped duplicate item keys, excess nesting, both altered digests, approved status, extra prototype key, lone surrogate, oversized astral-character note, numeric flag, foreign item, duplicated item, omitted item and blank flagged reason. All reject without changing existing notes.
- An older failed read cannot override a newer valid selection. Edits invalidate an in-flight read. A clear request invalidates a pending read; cancelling clear preserves edits.
- A missing last textarea after validation prevents all replacement writes; the same failure prevents clearing earlier rows.
- Input changes invalidate a clear confirmation. Explicit confirmed clear resets notes and flags; the existing download script exports the exact empty unverified template.
- Reordered and repeated imports map by item ID, do not append rows, and preserve literal script-like Unicode text. The unchanged export script's actual downloaded JSON passes the existing strict worksheet validator and HTML exporter, preserving both digests and escaped notes.
- Frozen file checksums remain unchanged.

The standalone parser is bounded, rejects duplicate decoded keys and uses null-prototype dictionaries. Full validation precedes confirmation and all controls are checked before assignment. Pending operations use generation tokens; successful restore triggers the existing unsaved-change signal. Imported notes are textarea values, not HTML. No identity/authorship assurance, fact approval, upload, persistent browser storage or model request was added.

Limits: browser-engine file picker/events, native save/cancel behavior, rendered layout and actual CSP enforcement remain unverified. The existing sandboxed Chromium startup failure was not retried or bypassed. These are protocol/data-safety tests with captured real-model artifacts, not new model evaluation or human investigator acceptance. No public listener, deployment, merge or remote changes by this reviewer.

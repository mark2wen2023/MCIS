# Explicit local worksheet restore (research only)

This opt-in extension adds a new generator without changing any previously frozen export files:

```sh
python research/semantic_support/render_restore_review.py \
  --corpus research/semantic_support/jiangxin9-provisional.json \
  --predictions research/semantic_support/jiangxin9-real-predictions.json \
  --output /tmp/my-restorable-review.html
```

Open locally, choose a previously downloaded worksheet JSON, then explicitly confirm replacement. Selection/validation alone does not change existing notes. Cancel preserves current edits; clear has a separate confirmation and can be cancelled. Editing while reading or while awaiting confirmation cancels pending actions. Repeated import replaces identical data, never appends duplicates. Rows map by itemId, independent of file order. After editing, use the existing explicit JSON download and strict CLI HTML snapshot workflow documented in BROWSER_EXPORT.md.

The parser rejects duplicate/unknown keys, invalid UTF-8, BOM, noninteger schemaVersion spelling, trailing content, excess depth, files over4MiB, changed corpus/model digests, other statuses, missing/duplicate/foreign items, nonboolean flags, invalid Unicode, notes over4000 code points and marked items without reasons. Entire document and all controls are preflighted before replacement. The only accepted status remains unverified_research_notes_not_case_facts. Source/model text stays unchanged. There is no identity attestation, author field, storage, network, upload, fact approval or new model call.

The additional script is CSP hash-pinned. Imported filenames and text are never inserted as HTML; notes are assigned to textarea.value. UTF-8/schema/digest failures use a generic rejection without echoing file content. A file is only read after explicit user selection. No existing downloaded file is deleted by clearing the page. Browser state remains ephemeral and exported files editable/untrusted.

Primary command: `service/.venv/bin/pytest -q research/semantic_support/test_browser_import.py`. Actual generated script runs under a minimal DOM/file adapter; tests cover two-step application, repeated/reordered imports, digest/status/schema/duplicate rejection, read failure/oversize, cancellation, input-change invalidation, late read suppression, clear/cancel and CSP hash inclusion. These are engineering protocol tests, not model capability or native browser acceptance.

Real browser validation remains blocked by the previously observed Chromium SUID sandbox configuration failure. No sandbox bypass or public listener. Native file chooser, downloads, rendered layout and actual CSP enforcement remain unverified. No merge/deploy. Independent acceptance and freeze are recorded alongside this file to keep all new work in research/semantic_support as requested.

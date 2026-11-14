# Explicit local research-note export

This is a bounded offline CLI, not a production workbench integration. It addresses the temporary research HTML controls' inability to create a saved review record. It does **not** read those controls automatically. The user explicitly generates and edits a local JSON worksheet, then exports a separate human-readable HTML file.

## Run

From `research/semantic_support`:

```sh
python export_review.py template --corpus jiangxin9-provisional.json --predictions jiangxin9-real-predictions.json --output my-notes.json
# Edit only item flags and note strings in my-notes.json.
python export_review.py export --corpus jiangxin9-provisional.json --predictions jiangxin9-real-predictions.json --worksheet my-notes.json --output my-review.html
```

Output files must not exist. They are created with mode0600. No output overwrite, network, model invocation, production DB, fact activation, authentication or automatic detection occurs. Generated HTML is self-contained with escaped text and restrictive CSP inherited from the existing renderer. Paths are caller-selected local files; the tool is not an API or permission boundary for untrusted remote callers.

## Binding and meaning

The worksheet contains exact raw-file SHA256 values for both the corpus and the predictions, with complete unique item coverage. Whitespace-only changes to input files invalidate the worksheet; regenerate deliberately rather than silently rebinding. Hashes are not signatures or proof of authorship/authenticity. Anyone who can edit local files can recompute them. Original model predictions, exact quote and source declarations stay separate from the appended note snapshot.

Three boolean flags request follow-up: time association, source association, other issue. A flagged item needs a nonblank reason. Unmarked does not mean checked, accepted or problem-free. There is no reviewer-name identity field, approval/verified status or formal decision. Notes are not evaluated for professional correctness. The HTML preserves original research controls as temporary inputs and explicitly states they do not update the exported snapshot. The exported snapshot is plain text at the end, with source/model/note-file digests. A person can edit any HTML copy; it is not a certified record.

## Limits and verification

Inputs use the existing strict 4MiB JSON loader, no duplicate/unknown keys, depth/budget and source digest checks. Notes max4000 Unicode characters each;1–100 unique items; generated HTML max9MiB. File write errors return a generic error and no success claim; a filesystem failure after file creation may leave an incomplete file and is not a successful export.

Primary tests:16 passed. Covers full real-output artifact roundtrip without API, immutable inputs, escaping, invalid/unknown metadata, item coverage, required note, types/budget, mode0600, existing-file and symlink overwrite denial. Data fixtures are public report-derived items and already captured real predictions. These are tool safety/format tests, not new LLM capability tests or authentic investigator review. No browser visual acceptance or CI pass claimed.

Independent review added10 checks; primary16+independent10=26/26. Final affected-directory regression149/149 passed (includes those26); official Pi Node fixture files both passed with zero provider calls. First isolated full run lacked the already-installed Pi dependency tree and failed4 fixture launches before requests; with the existing dependency tree available at its expected local location, all149 passed. No test expectations or product logic were weakened to obtain this result. See REVIEW_EXPORT_INDEPENDENT.md.

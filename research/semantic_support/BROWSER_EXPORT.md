# Offline browser worksheet download

Generate a new local page from the pinned public corpus and existing real model output:

```sh
python research/semantic_support/render_browser_review.py \
  --corpus research/semantic_support/jiangxin9-provisional.json \
  --predictions research/semantic_support/jiangxin9-real-predictions.json \
  --output /tmp/my-browser-review.html
```

Open that HTML file locally in a browser. Enter notes and flags, then click **下载当前研究备注 JSON**. Flagged items require a reason; notes are limited to 4000 Unicode code points. Confirm the actual download in the browser; initiation does not prove disk save. Cancellation/blocked downloads retain page state and permit retry. Repeated unchanged exports have identical JSON contents; browser download settings determine filenames, save location and overwrite prompts. The page does not overwrite files itself. Closing/reloading can lose edits; there is no automatic save, localStorage, upload, author field or import/resume function.

The JSON is the existing v1 worksheet, containing complete item IDs, unchanged corpus and prediction byte digests, three needs-check flags and exact notes. It does not bundle the original report/model output. Keep those files and run the existing strict exporter to produce a portable human-readable snapshot:

```sh
python research/semantic_support/export_review.py export \
  --corpus research/semantic_support/jiangxin9-provisional.json \
  --predictions research/semantic_support/jiangxin9-real-predictions.json \
  --worksheet /path/to/downloaded-notes.json \
  --output /tmp/my-research-snapshot.html
```

No new model calls occur. All notes remain unverified research notes, not authenticated investigator reviews or case facts. An unmarked checkbox never means verified, agreed or problem-free. Original source text, quotes, labels, explanations and source declarations are preserved by the unchanged renderer. Digests bind byte versions but do not authenticate files or authors. Edited page source is not trusted; the CLI revalidates worksheet schema, exact coverage, flags, Unicode, budget, required reasons and both bindings.

The generated page allows only the bundled script by its CSP SHA-256; connect-src/default-src remain none, with no external assets or network code. JSON is inert and HTML-sensitive content escaped. Legacy static pages and CLI stay unchanged. The generator refuses existing paths/symlinks. Its size budget is 8MiB.

## Verification

Run with the repository service virtual environment:

```sh
service/.venv/bin/pytest -q research/semantic_support/test_browser_review.py research/semantic_support/test_evaluate*.py research/semantic_support/test_render_review*.py research/semantic_support/test_export_review*.py
```

The Node harness executes the actual generated-page script with a minimal DOM/download adapter, then Python validates the downloaded JSON and exports the existing HTML snapshot. It covers empty export, missing reasons, Python-compatible whitespace, Unicode budget/lone surrogates, literal malicious notes, repeated downloads, simulated click failure/retry and object-URL cleanup. This is protocol and UI-state testing, not model capability, authenticated human review or browser-engine acceptance.

Browser plugin not available. Playwright with `/usr/bin/chromium`, `chromiumSandbox:true`, `file:///tmp/mcis-browser-review.html` failed before navigation: SUID sandbox helper is not correctly configured. No disabling of sandbox, public listener or deployment was used. Page identity, rendered layout/mobile view, CSP execution in a browser, native download cancellation and real filesystem download remain unverified; no screenshot or console-health pass claimed.

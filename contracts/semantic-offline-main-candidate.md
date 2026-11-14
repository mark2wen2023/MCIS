# Offline semantic worksheet: main-based extraction boundary

This candidate extracts exactly seven runtime files into research/semantic_support:
`evaluate.py`, `render_review.py`, `export_review.py`, `render_browser_review.py`,
`render_restore_review.py`, `browser_review.js`, `browser_import.js`.
The first three are pinned from PR56 head254167e; the latter four from PR57
head2104fcbe. No PR56 ancestry, production route, identity adapter, model transport,
Pi harness, database or network integration is included. Source-manifest.json under
SEMANTIC_MAIN_CANDIDATE records all40 selected files and original byte hashes;
tests, fixtures and historical provenance documents are not runtime dependencies.

Keep source files co-located. Caller supplies bounded corpus/prediction snapshots;
the CLI reads their exact bytes and calculates both hashes. Do not expose direct
Python functions as an API accepting untrusted caller-declared digests. Preserve
all JSON validation, Unicode code-point distinctions, HTML escaping and hashed
script CSP. Do not reformat source JSON or mutate the frozen renderer structure.

Notes remain `unverified_research_notes_not_case_facts`. Import must match corpus
and prediction hashes plus complete item coverage, require explicit replacement,
and retain current edits on invalid input/cancel/late reads. Clearing is separately
confirmed; unmarked does not mean verified. Download means initiated, never proven
saved. CLI exclusively creates0600 outputs and refuses overwrites. No automatic
storage/upload, fact activation, author authentication, source PDF retrieval or new
model call. Original model labels/rationales/source declarations stay visible.

The Jiangxin9 files are historical unverified outputs from a prior documented run;
this extraction neither repeats nor authenticates that run, model identity or source
PDF. Scripted fixtures remain explicitly scripted. Historical acceptance documents
and freezes describe their original branches; the new candidate freeze and report
are authoritative for the extraction. Main's production authentication and attachment
issues are not addressed by this offline tool.

Candidate tests use generated pages with Node adapters, not a browser engine. Native
file chooser/download, actual CSP enforcement and layout require supported sandboxed
browser acceptance. Do not bypass the sandbox to claim completion. A formal workbench
entry point, authenticated identity or model execution requires a separate contract.

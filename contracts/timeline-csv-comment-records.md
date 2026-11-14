# Registered CSV: W2 comment-line semantics

## Actual defect reproduction
A CSV with unmapped `note` as its first column can contain a valid record whose
raw first field begins `#memo`. Python validates the mapped time and number,
but W2 VdrCsvImporter silently skips physical lines beginning # after trimming
(and stripping one leading BOM). For a90 observation in such a row and a later
normal50 row, comparison against50 returned200, no conflicts and no diagnostics:
the expected40 difference vanished. Reproduced once on unchanged actual W2 with
real service/SQLite registration before modifying the validator.

## Correction
The registered preview preflight checks physical lines using W2's comment-prefix
shape and refuses them with422 TIMELINE_SOURCE_CSV before calculation. It does
not delete the row, rewrite raw evidence, or silently re-quote it. The message
names the unsupported unquoted leading # form. An explicitly quoted `"#memo"`
first field or # elsewhere remains supported and actually computes delta40.
Existing multiline-cell and ambiguous-header rejection remain in force.

Scope remains the registered-preview service path. This does not alter the core,
generic inline CSV endpoint, original files or observation approval. It is not a
claim of complete Python/.NET CSV equivalence; future expansion should use a
shared strict dialect contract and regression cases, not assume all valid CSV
is safe for this importer.

## Primary acceptance
New test_registered_comment_records.py:6 pass, zero skips. Four comment-like
prefixes fail before core without raw mutation; two legitimate first-field
forms execute actual W2. Historical pre-fix actual-core reproduction:1 pass.
Independent/regression results recorded below. Native subtasks, no deployment
or merge, no browser/LLM/CI/full-system claim.

Final focused regression:99 pass, zero skips, including new6, earlier multiline13,
header14, registered, independent, timestamp and parent-report suites. Includes
actual W2 and existing loopback HTTP. Independent new9 and combined46 pass,
zero skips (counts overlap); new9 separately rerun by implementer. Covers later
rows, CRLF/CR, comment-like headers, tabs/Unicode whitespace+BOM and actual-core
quoted #/comma compatibility. Existing Starlette deprecation warning only.

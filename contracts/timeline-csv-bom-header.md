# Registered CSV first-header BOM audit

Actual W2 removes leading U+FEFF characters from its first parsed header before
trimming/comparing names. The earlier alias check did not include this rule.
A CSV `"[BOM]heading",heading,utc` with `90,45,T` selected by `heading` passed
Python validation for45 but actual W2 computed90, giving delta40 against50
instead of delta5. Historical service/SQLite/actual-W2 reproduction passed once
before this patch. Bracketed [BOM] here denotes the real U+FEFF character.

The collision key now strips BOM characters from the first parsed header only,
then uses the existing strip/casefold check. Original header strings and raw
bytes remain unchanged; ambiguous input rejects before core. Normal UTF-8 BOM
file intake still computes correctly. This is not blanket removal of BOMs from
all fields and is not generic CSV dialect normalization.

## Current narrow supported boundary
- Registered local UTF-8/UTF-8-BOM CSV, explicit unique exact mapped column names.
- Headers must not alias under the conservative W2-compatible collision check.
- Every mapped timestamp has an explicit supported ISO offset; quantities use
  finite ASCII numeric grammar and existing heading/speed range validation.
- Single-line quoted fields, escaped quotes and LF/CRLF record separators work.
- Embedded CR/LF in headers/cells and raw comment-like # records are refused,
  including unmapped fields, rather than silently changing observation counts.
- These local guards do not establish all Python/.NET Unicode/CSV equivalence,
  sensor authenticity, source independence, calibration or fact approval.
- Generic inline CSV preview and legacy core entrypoints are outside this guard.

Primary test_registered_bom_header.py:4 pass, zero skips (three ambiguous first
headers rejected without raw mutation, one actual-W2 ordinary UTF-8-BOM case).
No UI/browser/LLM/CI/full-system claim; no merge/deployment. Native implementation
and independent native review. Final regression and independent counts below.

Final focused regression:112 pass, zero skips, including actual W2 and existing
HTTP tests. Independent new6/combined42 pass, zero skips; new6 also rerun by
implementer. Counts overlap. Time-column BOM aliases refused; actual W2 confirms
non-first-column BOM and first-column space-before-BOM are not mistakenly
stripped (expected deltas5/40/5). Raw bytes unchanged. Existing Starlette warning.

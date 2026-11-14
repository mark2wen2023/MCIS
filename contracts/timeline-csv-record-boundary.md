# Registered CSV logical-record / physical-line audit

## Real reproduced defect
Python csv.DictReader accepts quoted multiline cells. W2 AlignCommand breaks
text into physical lines before VdrCsvImporter reads individual lines.
A registered CSV with one observation and an unused quoted note:

```csv
utc,heading,note
2026-05-18T06:15:00Z,45,"memo
2026-05-18T06:16:00Z,90,end"
```

has only one logical measurement (45). The old service validated that record,
but actual unchanged W2 treated the note continuation as a second measurement90.
Compared to a second source at06:16 with50 it returned a phantom delta40, with
empty importDiagnostics. Historical pre-fix API/SQLite/actual-W2 reproduction
passed once before changing the validator; not a speculative or fake-core claim.

## Small correction
Reject CR/LF embedded inside any header or cell, including unmapped fields.
Return422 TIMELINE_SOURCE_CSV before W2 runs; error now states this limit.
Ordinary record terminators and single-line quoted cells/escaped quotes remain
supported. No flattening, sanitizing, rewriting or automatic observation approval.
Users must prepare a separate traceable single-line-per-record derivative; the
original registered file remains untouched. The service does not do that for them.

This restriction intentionally rejects valid general-purpose multiline CSV
because the selected core importer does not implement that dialect. Header-alias
rejection from502d205 remains intact. This audit does not claim exhaustive parser
equivalence, semantic extraction correctness, true sensor provenance, clock
calibration, persistent binding or human fact review.

## Verification
Primary test_registered_multiline_cells.py:5 pass, zero skips. LF/CRLF/CR embedded
notes are rejected before controlled core; raw bytes unchanged. LF/CRLF ordinary
single-line quoted CSV executes actual W2 with expected delta40.
Historical pre-fix reproduction:1 pass. Final regression/independent counts below.
No browser, LLM, CI, full-system, merge or deployment claims.

Final focused regression:85 pass, zero skips (new5, earlier header14, registered,
independent, timestamp and parent-report suites). Independent review adds8:
CR/LF in unused headers, mapped time/value cells and later rows rejected; ordinary
multi-record LF/CRLF, empty quoted fields and literal backslash-n remain valid
with actual W2. Independent combined45 pass, zero skips; counts overlap.
Independent8 separately rerun by implementer. Existing Starlette deprecation only.

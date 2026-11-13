# Registered CSV: reject ambiguous core column aliases

## Observed risk
The Python preflight validates CSV headers by exact spelling. The existing W2
VdrCsvImporter uses Trim + OrdinalIgnoreCase and keeps the first matching header.
For `utc,heading,Heading` containing `...,45,90`, choosing `Heading` passed Python's
validation for 90 but W2 read 45. A second source at 50 produced delta5, not40.
This was reproduced before the patch using actual unchanged W2 through the real
service/SQLite intake, not a fake model or inferred-only code review (1 test pass).

## Narrow correction
Preflight rejects header names that collide after strip/casefold. The check is
conservative rather than an exact implementation of .NET Unicode comparison.
It does not rename, normalize or rewrite original bytes. Unique mixed-case and
padded headers remain accepted when explicitly selected. The wire schema and
W2 algorithm are unchanged. Ambiguous input returns422 TIMELINE_SOURCE_CSV before
core execution. This applies to every header, including unmapped columns.

The correction only targets header aliases. It does not certify all cross-runtime
CSV grammar equivalence, semantic extraction, source independence or observation
approval. Same-version SHA verification alone would not catch this parsing issue.

## Primary tests
service/tests/test_registered_header_aliases.py: four ambiguous forms refused
before core, raw bytes unchanged; two unambiguous forms execute actual W2 and
return expected delta40 (synthetic data). The historical reproduction used the
same source file from remote a8cfc4f (Git blob11420280b1b6ce6b3701dc152de3317aaefd81c9).
The reproduction is recorded rather than kept as a test expecting unsafe output.

No merge/deployment; no browser/LLM/CI claims. Native implementation and separate
native review subtasks. Final regression and independent counts recorded below.

Final verification:72 focused primary/regression tests pass, zero skips, covering
header aliases, registered preview, independent registered checks, timestamp
syntax and parent-report paths. Includes existing actual W2/loopback acceptance.
Independent reviewer added8 tests (time-column aliases, unmapped aliases,
Unicode conservative collisions and real-W2 unique time-name compatibility);
32 combined independent/primary/registered tests pass, zero skips. Independent8
also rerun separately by implementer. Counts overlap; not 112 distinct tests.
Only existing Starlette TestClient deprecation warning. Initial isolated setup
lacked report seed files and did not run; restored same-version seeds before the
successful historical reproduction and all reported successful runs.

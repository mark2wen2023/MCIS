# CPA sampling bounds: independent review (2026-11-12)

## Verdict
No blocking issue found in this narrow availability fix. The implementation limits the actual sampler to 5001 stored values and rejects a non-advancing finite increment. Non-finite query values and non-finite stored default duration are rejected before interpolation/core calls. Case lookup and permission checks remain before sampling validation.

Reviewed router SHA256: `11e72064fd10b3961ad6afb0f0bdbe2e0de4532b39d13f2cc1732412bec73d21`.

## Independent verification
`service/.venv/bin/python -m pytest -q -p no:cacheprovider tests_acceptance/CPA_BOUNDS`: **18 passed**, one existing Starlette/httpx deprecation warning, 3.40 s. Exact output: `logs/cpa-bounds-independent.log`.

- Three stored-default-duration non-finite cases.
- Five hazardous grids: smallest subnormal step, positive/negative huge non-advancing values, infinite endpoints, and tolerance-amplified tiny finite step. A round-call counter bounds the test itself to 5001 iterations. Both interpolation and core spies remain untouched.
- One test checks 400 deterministic random finite grids against a bounded legacy cumulative-addition reference, exactly including three-decimal rounding and endpoint tolerance. This is 400 generated comparisons inside one pytest item, not 400 test items.
- Three 5000-interval boundary cases, including the preserved 1e-9 endpoint tolerance.
- Six HTTP tests, one per declared role, each testing four invalid requests against a fresh synthetic seeded SQLite database. HTTP returns 422 BAD_RANGE, no interpolation/core invocation, and unchanged database file hash. These do not test production authentication.

Implementation tests separately cover default end, empty reverse intervals and explicit case-policy denial order. Independent reviewer did not edit implementation or existing tests.

## Compatibility and limits
The actual 5001-point cap intentionally rejects tolerance-expanded grids that previously exceeded the nominal 5000-interval budget. This is disclosed in CONTRACTS/OpenAPI, not claimed as byte-for-byte compatibility for every finite input. Ordinary finite cumulative grids are unchanged. The loop bound is narrowly scoped: it does not bound raw core inputs, total concurrent requests, other endpoints, or subprocess output. Old raw align filesystem exposure and header-declared identity are not fixed. No browser/Unity/full-project or production deployment acceptance is claimed here.

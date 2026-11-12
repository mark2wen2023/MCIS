# CPA_BOUNDS independent acceptance

## CPA-B01: non-terminating or excessive case CPA sample generation

Cause: non-finite parameters and floating-point stagnation can bypass the nominal interval check; an absolute endpoint tolerance can turn a nominal zero-width interval into an enormous grid.

Reviewed resolution: finite parameter/default-duration checks, actual 5001-point cap, and strict progress check before any interpolation or core invocation. Cumulative stepping, endpoint tolerance and rounding remain unchanged for accepted finite grids.

Status: independently accepted as a narrow availability fix. `tests_acceptance/CPA_BOUNDS/test_independent.py`: 18 passed, including 400 deterministic parity comparisons in one test; see `logs/cpa-bounds-independent-review.md`. No implementation changes by reviewer; no merge/deployment authorization implied. Authentication and old raw align issues remain outside scope.

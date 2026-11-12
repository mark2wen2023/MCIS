# CPA bounded sampling verification

## Scope and provenance

Implemented against main `c54990c6e711339ccb633c57b0b467b73def0479`, then integrated atop `39659932e4f3e1240624566401ecc76ec9cefc4b` (W16 font fix retained). This is an isolated partial snapshot, not a full clone. Original service/contracts and supporting assets came from the previously blob-verified canonical restoration; the W13 service changes and all W16 font changes were refreshed from exact current commits. The production font matches Git blob `102a717709c10b1ffcfdc4bb35fb335124319e85`. No assertion or fixture was weakened to accommodate source drift.

Only the case-scoped CPA sampler changes: reject non-finite inputs/effective defaults, stop a non-progressing floating-point increment, and enforce a hard 5001-sample limit before interpolation or core execution. Keep cumulative stepping, three-decimal rounding, endpoint tolerance, normal response shape and permission order. The actual cap intentionally rejects pathological tolerance-expanded finite grids. Raw `/core/align`, authentication, subprocess resource limits, database migrations and deployment are outside scope.

## Verification history (failures retained locally)

- Original-main full service baseline: 438 passed / 1 failed. The only failure was the custody compat launcher using its unset `DOTNET_ROOT`, not a product defect. Supplying the existing verified SDK location fixed this environment issue without changing the script/test.
- Initial new regression red run: 17 passed / 12 failed. Eleven failures exposed the sampling defect. One assertion incorrectly assumed Public had no `ais_sim` access; that existing policy allows reads. The test was corrected to explicitly set a deny policy and verify authorization ordering, not deleted. A 5002-step test tripwire safely prevented legacy unbounded loops from exhausting resources.
- Focused final self-test plus contracts: 33 passed (29 new regression items + 4 contract items).
- Independent suite: 18 passed, including 400 random valid-grid exact comparisons inside one test; six role-specific HTTP tests also prove no database mutation. See `cpa-bounds-independent-review.md` and `DEFECTS/CPA_BOUNDS.md`.
- Full service with the fix on c54990c: 468 passed, no skips, 125.94 s. The corrected environment supplied both `MCIS_DOTNET` and `DOTNET_ROOT` to the existing wrappers.
- Existing HTTP core error/envelope acceptance: 75 passed. The first collection attempt omitted `PYTHONPATH=service`; after supplying it, all 75 passed without changes.
- Provenance tests: 9 passed.
- Final current-main integrated run: pending at report preparation; result appended below only after completion.

Both CPA implementation freeze (4 files) and inherited W16 freeze (5 files) match before the integrated run. No Web, Unity/editor, or full C# acceptance suite is claimed. Core-backed service tests execute the verified local SDK/core build; independent sampler tests use synthetic spies to measure rejection and exact grids.

## Final integrated result

On current main `39659932e4f3e1240624566401ecc76ec9cefc4b` plus the frozen sampler change, the combined command (`PYTHONPATH=service`, verified SDK environment) completed with **572 passed, zero failed, zero skipped, 131.36 s**: service 470 + independent sampler 18 + existing HTTP core safety 75 + provenance 9. Exact output: `logs/cpa-bounds-main-integrated.log`. Both freeze lists still match. Targeted Python compileall also passed. No CI result is inferred from this local result.

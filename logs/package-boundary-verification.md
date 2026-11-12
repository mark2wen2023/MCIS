# Package ZIP decoding boundary verification

## Scope and provenance

Base main `d695134ba74d1c3cf79f802eeaaf6b8f697f85fc`, tree `b679acfc2fb9510a0345a9a29dc2a420dbce026b`. Isolated workspace was materialized by exact Git blob SHA matches against that tree: 584 tracked files copied, 848 unavailable, all service files present. It is a partial snapshot, not a full clone. Existing verified SDK8.0.428 and Python dependencies are reused; local core/compat build outputs are copied for running tests and are not publication entries. No existing source/test assertion/seed was altered except the package decoder and explicitly new tests.

Implementation scope: inventory/path ambiguity checks before payload decoding and stable 422 BAD_PACKAGE on malformed/encrypted/unsupported ZIP data. Existing valid package bytes, supported compression and Unity backslash paths preserved. Only production file changed is `service/mcis_service/package/mcase.py`. W8.2 case-create frontend and shared entrypoints untouched.

## Results

- Red reproduction before implementation: 21 failed / 21 passed, including original 8 package tests. Retained exact output `logs/package-boundary-red.txt`. Failures are accepted ambiguous paths or unhandled parser exceptions, not weakened legacy expectations.
- Self-tests and existing package/contract regression: 46 passed, no skipped, 6.87 s (`logs/package-boundary-selftest.txt`): 34 new decoder/HTTP cases, 8 original package cases, 4 existing contract cases.
- Independent acceptance and aggregate status will be appended after final review and completion.

## Limits

No new browser, Unity/editor, whole-C# or deployed acceptance claimed. Upload and decompression budgets are explicitly not implemented: valid large evidence packages remain supported with the pre-existing unbounded memory behavior. This does not validate manifest JSON/schema, authenticity, case IDs, cross-document consistency or atomic filesystem import; it does not establish production authentication. A successful hash check proves content matching the supplied manifest, not trusted authorship. No deployment.

Inherited freeze checks: five W16 font entries and three Core-finite entries match. CPA route/test/OpenAPI entries match; its older CONTRACTS.md hash differs because Core-finite subsequently updated that shared contract. The current contract byte-for-byte matches the d695134b remote Git blob and the newer Core-finite freeze. No old freeze was rewritten to hide shared-file history.

Final-code tests on the original d695134b base: independent 61/61 passed (7.05 s) after the ancestor-collision correction; original 58 green / 3 added red evidence preserved. Final aggregate `service/tests + CPA_BOUNDS + HTTP_CORE_ERRORS + provenance + PACKAGE_ZIP` passed **690 items, no failures or skips**, in 149.88 s. Separate CORE_FINITE acceptance passed **43**, 3.45 s, giving **733 distinct pytest items** combined. Breakdown: service 527 (493 existing + 34 new), CPA18, priorHTTP75, provenance9, ZIP61, corefinite43. Previous implementation aggregate629 is retained but not substituted for final-code results. Final self/package/contract run46 passed6.16s. No new defect remains in the specified ZIP decoder scope.

These are not yet validation of the W8.2 integrated base: publication/integration waits for its exact merge commit and a subsequent final combined check.

## W8.2 integration

Integrated exact main `37bbeb2d8694a7ac3b267cf9a3c0bcad263b5d07`, tree `c080264accec49a382dd13507e56beab6220ef30`. All 41 changed W8.2 blobs were copied only after matching their Git SHA; none missing. Independent reconciliation: 621 available tracked files exactly match this new base, 843 are absent, and three deviate: the intentional package decoder plus two locally rebuilt compat DLL/PDB runtime outputs. Those binaries are excluded from publication. All 14 package/W8.2 frozen inputs match. Independent61 rerun passed7.39s unchanged.

W8.2 real HTTP regression: 13 passed, 1 existing strict xfailed (the API's date-time schema validation gap already documented by W8.2),1.90s. The xfail is not a passing test and was not introduced or hidden by this package change. Web build/typecheck and W8.2's106 assertions passed; output includes an existing Vite bundle-size warning. Browser screenshots were not rerun because no UI code is changed by this slice.

Final W8.2-integrated aggregate completed: **690 passed**, zero failed/skipped,147.65s (`logs/package-boundary-w82-integrated.txt`). Separate unchanged CORE_FINITE suite:43 passed3.81s. Combined733 distinct pytest items pass on the integrated code. Separately W8.2 HTTP13 pass/1 previously documented xfail; Web build/typecheck and462 assertions (18+58+38+148+94+106) pass. W8.2's xfail and Vite/dependency warnings remain disclosed and are not counted as passing. Current source freeze and inheritedW8.2 freeze match; no published binaries or runtime data.

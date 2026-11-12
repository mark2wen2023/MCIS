# Core response finite JSON verification

## Scope and provenance
Based on main `74433ebbde9290f06a70fc7feea4ec0a8b3176fb` (tree `9f397437275db1299a12791544c8d0f3987c89c2`). Only Python core response decoding changes: reject NaN/Infinity and overflow-to-infinity literals before downstream use; retain finite numbers, integers, strings, extra fields, domain mappings and last-line protocol. Existing HTTP redaction returns CORE_BAD_OUTPUT/502 without original core output.

The local validation workspace is a partial snapshot inherited from the preceding verified CPA integration, not a full clone. Rechecking all available tracked inputs against the current remote Git tree found 407 matching blobs, 1011 absent files and three known local-only mismatches: an older handoff document and rebuilt compat DLL/PDB. All available service source, schemas, font and C# source inputs match main before the explicitly listed change. The handoff and rebuilt binaries are NOT publication entries. The CLI wrapper executes reproducible builds from source; provenance tests cover the core seed chain. No assertion or fixture was weakened to accommodate drift.

## Checks and retained failures
- New red regression: 15 failed / 8 passed. All 15 failures reproduce acceptance of non-finite response numbers or wrong domain-error mapping, before the implementation edit. Exact output retained locally in `logs/core-finite-red.log`.
- Self-tests + contract tests: 27 passed (23 new numeric tests and four existing contracts), 1.47 s, `logs/core-finite-green.log`.
- Independent acceptance: 43 passed, including 400 randomized finite-envelope comparisons within one item; 30 HTTP cases prove exact redacted 502 and no SQLite mutation. See `logs/core-finite-independent-review.md`.
- Existing HTTP safety acceptance: 75 passed on the candidate service, independently rerun without changes.
- First aggregate invocation used a nonexistent `tools/tests` path: zero tests ran. This command/setup error is retained in `logs/core-finite-collection-error.log`; corrected to `tools/provenance/tests` for the actual run.
- Freeze list (three files) matches; targeted Python compileall passes.

## Limits
No new Web, browser, Unity/editor or full C# suite is claimed. Malformed-child tests use synthetic subprocess output through the real FastAPI application. Real CLI execution is covered separately by the aggregate service suite. This is not a resource cap for all subprocess output, arbitrary JSON nesting or concurrency, and does not fix old raw align file access or header-declared identity. No deployment.

## Aggregate result
Pending completion; appended only after the command exits.

Corrected aggregate command completed with **595 passed, zero failed, zero skipped, 139.42 s**: service 493 + CPA independent 18 + prior HTTP safety 75 + provenance 9. SDK environment: MCIS_DOTNET/DOTNET_ROOT point to the existing verified SDK8.0.428; DOTNET_CLI_HOME points to the existing isolated SDK home; PYTHONPATH=service. Exact output: `logs/core-finite-integrated.log`.

The coordinator also reran the frozen new independent suite: **43 passed** (3.33 s, existing Starlette warning), `logs/core-finite-independent-coordinator.log`. Across aggregate plus new independent suite there are **638 distinct pytest items**, not 638 new tests. The three current freeze entries and all five inherited W16 font freeze entries match; CPA router remains byte-for-byte unchanged. No GitHub CI pass is inferred from these local results.

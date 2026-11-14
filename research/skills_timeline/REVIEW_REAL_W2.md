# SK-T01 real W2 roundtrip independent review

Date: 2026-11-13. Executor: native implementation subtask plus a separate native
review subtask, not a separately running Codex application.

## Source and build evidence
Core input tree: PR56 `80b27b6c22c5b62ca4d4388da42c51094063a995`.
Clean selected files verified against remote Git blob SHA values before use.
No dirty working-tree code or previously built binaries used for execution.
Official .NET SDK 8.0.428, installed runtime 8.0.34.
The standard build failed on NuGet-Migrations named-mutex initialization.
The replacement acceptance recipe directly invokes the SDK compiler using the
unchanged package-free project's Compile globs: 55 C# files and installed net8.0
reference assemblies. No NuGet access, permissions override or core source edit.
This is NOT normal MSBuild/CI verification.

## Executed
- 67 existing synthetic protocol/unit tests.
- 6 real-engine tests in test_real_w2.py: conflicting/equal heading, disjoint
  time, invalid checksum, unparsable NMEA, post-compute repository recheck failure.
- 4 independently authored real-engine tests in test_independent_real_w2.py:
  angular wraparound, reversed source ordering, missing log timestamps, and
  equivalent explicit +08:00 versus UTC times.
- Independent combined rerun: **77 tests passed, zero skipped** against the
  freshly rebuilt DLL. No blocking defect found within this test-only scope.

## Limits
Real W2 execution uses fictional NMEA; it does not certify real evidence,
clock calibration, per-source coverage completeness, event identity or causality.
Principal/repository/revocation are synthetic doubles, not database permission
integration. No actual LLM, service/API/UI, production transport, persistence or
archive tested. Test subprocess has a timeout but not a production streaming
output/resource cap, cancellation service or process isolation contract.
The six plus four real-engine cases are opt-in; missing developer paths cause
skips, not passes. No merge/deployment. Draft research scope remains appropriate.

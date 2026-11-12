# W12.2 additional synthetic boundary verification

2026-11-13 06:30 UTC+8. Target parent draft d833f52e863aae2452d84f2cbf640e97d565db47.

Independent review and rerun of service/tests/test_cpa_boundary_0530.py: 13 passed in 1.85 s. Existing Python virtual environment only; no dependency installation, NuGet/.NET invocation, actual core calculation or browser execution. Production code unchanged.

Checks cover malformed core envelopes, commands, versions and result types; negative distance, nonfinite TCPA, contradictory degeneracy; invalid stored timestamp/precision, nonfinite SOG/COG and boolean heading. Core functions are mocked or asserted not to execute. Invalid responses have no rows and retain Cache-Control: no-store.

This is scoped synthetic API evidence, not CPA numerical correctness, whole-project acceptance, browser acceptance or CI. Draft remains blocked on real-core and browser validation. Prior test counts overlap and must not be summed into completion percentages.

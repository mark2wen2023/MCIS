# W14.4 fixed-rudder response preview

Run `tools/mcis-nomoto/mcis-nomoto.sh`, no arguments, stdin parameters per
`contracts/nomoto-preview-v1.md`. Requires existing .NET SDK8.0.428 and Python3
on Linux; MCIS_DOTNET selects the SDK. No package installation or external calls.

Thirteen original source files are explicitly compiled without modifications.
GeoMath.cs is additionally needed by implementations sharing IGeoConverter.cs.
Some dependency files contain CPA/collision-related types but those computations
are not invoked. Only NomotoSimulator.Simulate is used, with no interventions for
the baseline and one Turn at t=0 with headingChange=0 for response. No PD hold,
anchor, speed change, collision, risk or W11 adapter is invoked.

All active values are manual decimal strings, notes required. Both trajectories
are hypothetical. Initial local origin, time, ROT and actual rudder are zero.
Unused ManeuverParams values speed/stop/astern constants, LOA/beam/displacement
are 1, minimum speed0; explicit AnchorParams are 0/0/0/1/1. These are constructor
compatibility values, NOT vessel attributes or estimates. Tests vary them to7
without changing response. ManeuverParams.Default is never used.

Core trajectories are evaluated at steps0.1 and0.05 seconds; output uses every
10th actual coarse sample at integer-second grid points, checking time rounding
within1e-7. Endpoint differences compare final core outputs, not extrapolations.
Step comparison is NOT an error certificate, confidence interval or real-vessel
validation. RK4 with stepwise rudder does not imply universal fourth-order error.
Input/output limits are engineering bounds, NOT physical or navigational limits.

Protocol rejection exits4; operational failure is nonzero, no partial success.
Build failure can produce no JSON. Diagnostics stderr, result stdout. Receipt
contains source/artifact hashes and deterministic build configuration. Generated
out/ is not for publication. No sources or case databases are read by this CLI.

Synthetic tests: `python tools/mcis-nomoto/test_cli.py` with MCIS_DOTNET set.
Rebuild test invalidates only this adapter's receipt; run while adapter idle.

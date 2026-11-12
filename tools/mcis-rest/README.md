# mcis-rest (W18.3 adapter)

Standalone .NET 8/C# 9 JSON adapter over unchanged `RestHours.cs` and `Result.cs`.
It does not modify or rebuild `mcis-core`, W12 artifacts, or domain rules.

Run `MCIS_DOTNET=<existing-dotnet-8.0.428> DOTNET_CLI_HOME=<writable-directory> ./tools/mcis-rest/mcis-rest.sh` with one JSON object on stdin. The wrapper builds only this adapter when its content-addressed receipt/artifacts differ. Build diagnostics go to stderr, protocol to stdout. No new package dependencies.

Success: exit 0, `{ok:true,result:...}`. Domain/input rejection: exit 4, `{ok:false,error:{code,message}}`. Unexpected computation failure: exit 1. Build/startup failures may have no JSON response and must be handled as unavailable by callers, never as a valid empty result.

Input is exactly `recordStartUtc`, `recordEndUtc`, `intervals`; intervals contain exactly `startUtc`, `endUtc`, `kind` (`Watch`, `OtherWork`, `Rest`). UTC whole-second Z timestamps, years 1900–2100, positive record length at most 14 days, 1–256 intervals, 128KiB request maximum are engineering constraints, not professional rules. Duplicate/unknown fields are rejected. Missing time remains Unknown, never inferred rest.

Fixed rest-baseline mode disables work-hour limits. No caller thresholds/exceptions. `coverage.has24hWindow`/`has7dWindow` describe only available window length, not complete evidence or legal applicability. Output contains totals, findings, insufficientData and unchanged core assumptions with additional scope caveats. No overall compliance Boolean. Finding timestamps preserve fractional core boundary precision.

`out/build-manifest.json` records source SHA-256, build recipe, SDK and artifact hashes. Build lock serializes cold builds; artifacts/receipt replace atomically. `out/` is generated and must not be published.

Synthetic self-test: `python tools/mcis-rest/test_cli.py` with the same environment. Cold-build test cleans only this adapter's generated output, so run before simultaneous application tests.

# W11 real ECFC core gate (synthetic)

This optional acceptance harness does not change the MCIS launcher, C#, service, .mcase policy, or browser pilot. It pins four helper blobs from `b40a6cacf91ba0d8b297377d31162e404e468e8d` and checks the 186 existing W11 source/service blobs plus the unchanged ECFC launcher, build recipe and seven declared inputs from `d9187fef1f979866ac4d8ce2064d1ac92f34bb36`. It stages them in a fresh temp directory, with the launcher at its original relative path and executable mode. Do not bundle product source or the SDK in the test commit. The `--source-dir` options can be repeated for disjoint **existing** input trees. In particular, the service/core and T+109 synthetic marker may be supplied by separate exports; the marker must match the prior pinned W11 manifest.

Check sources without a runtime:

```bash
python3 -B tests_acceptance/w11-real-core/run.py \
  --pilot /absolute/verified-b40a6ca-checkout \
  --source-dir /absolute/local-pinned-service-and-core \
  --source-dir /absolute/local-pinned-w11-synthetic-marker --verify-only
```

On the **same** allowed Linux runner with already-installed SDK **8.0.428**, repeat replacing `--verify-only` with `--dotnet /absolute/preinstalled-sdk/dotnet`. The preinstalled Python product requirements must already be available too. Do not install packages, widen permissions, bypass local startup errors, or use external feeds. The launcher is called with an empty local package feed, telemetry disabled, and isolated CLI home; runtime errors stop the gate. SDK version and NuGet initialization, original CLI smoke and manifest integrity, and the actual business gate have separate receipts. The smoke validates original source and generated artifact digests, not business behavior.

If the original fresh-home run stops at the existing `NuGet-Migrations` preflight, an explicit alternate harness mode is available. Run **only** on an existing offline Linux runner with only loopback, using the real login HOME of an already successfully initialized SDK 8.0.428. Use the existing service Python as the outer interpreter and append `--initialized-home` to the full invocation above, retaining the explicit `--dotnet`. Do not copy or manufacture migration state, drop the original NuGet check, or run outside offline isolation. The mode preserves HOME but not an inherited DOTNET_CLI_HOME; restore, HTTP, and plugin caches are task-local, with an empty restore source and no fallback. SDK/version, NuGet preflight, launcher, manifest and every business assertion are the same. Any new runtime failure is a blocker. Record this mode by its own candidate SHA and retain the original blocked receipt; do not claim the fresh-home run passed.

Only after smoke: using the approved synthetic file, temporary SQLite, and original fixed Python router, preview the synthetic graph through the actual C# core; verify nothing was saved yet; save with the existing explicit archive limitation acknowledgment; dispose the SQLite engine and reopen the same case; verify document, revision, draft/ToBeVerified labels, one request and one corresponding audit. No fixture core is installed. Nothing reads the user's data, starts an externally listening host, changes the production page, or claims browser/real association replay/archive validation.

Local readiness baseline: source-only preflight passed with `186 originals + 4 pilot helpers + 9 exact core blobs/modes`. No executable SDK found in the available local runner; the full invocation with an absent SDK path correctly exited 2 before smoke, core invocation, preview, save, or reopen. This is not a successful real .NET or W11 verification.

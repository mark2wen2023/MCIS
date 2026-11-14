# HFACS environment diagnosis

Baseline: origin/main 73fc8002868d9c6894b5fce6d03f7db690291bf6.
Branch: fix/hfacs-environment-diagnostics. No service/core/build recipe/test
fixture changes; no deployment, merge, SDK installation or remote push.

Actual isolated reproduction: the two main archive coexistence scenarios fail
at run_core(taxonomy), both HFACS_CORE_UNAVAILABLE (2 failed in 1.54s).
The actual wrapper returns 1, zero stdout, FileNotFoundError for default dotnet.
The offline checker reports SDK_MISSING; DLL and manifest absent. These facts
identify this environment's immediate failure before the real C# build, not a
proven archive implementation failure. They do not prove the build will succeed
once SDK is supplied. Missing DLL is downstream of absent build prerequisites;
a clean checkout intentionally does not contain generated binaries.

Product behavior already fails closed with HTTP 503 on unavailable/invalid core.
No alternate taxonomy/inference or successful validation is invented. The small
candidate improves operator diagnosis only. It loads the exact build recipe
constants without invoking build(), probes configured dotnet --version with a
5-second timeout, and never prints subprocess diagnostics/environment values.
DLL presence is expressly not validation. README documents real follow-up gates.

Validation: 11 diagnostic unit tests passed in 0.05s (process doubles; NOT real
.NET or model validation); actual CLI and two actual service tests above. See
unit.txt, main-two.txt, environment.json, wrapper.json and independent review.

Limitations: genuine SDK8.0.428 and actual C# build/core/combined archive success
remain unverified. No claim about all other historical suite failures. Real
browser acceptance remains blocked by the previously recorded sandbox issue and
was not attempted here. Existing untrusted role headers/identity, long lock and
memory limitations unchanged. No new skip, fallback or production readiness.

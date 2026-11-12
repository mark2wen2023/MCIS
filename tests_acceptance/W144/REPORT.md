# W14.4 Independent acceptance

## Result
- **29 passed: 14 mathematical/CLI tests and 15 API tests**, all synthetic and demo seeding disabled.
- Real CLI + FastAPI + Vite + headless Chromium passed: blank mandatory numeric inputs/notes, explicit parameter/source entry, two hypothetical trajectories, square equal-metre plotting region, integer-second state table, numerical-step disclaimer, wrong digest rejection, editing and delayed replies after case/identity changes invalidated.
- Frozen implementation hashes verified. Thirteen existing C# dependency sources and original mcis-core DLL match prior baseline. Isolated test variants never modify or rebuild the original core.
- No new product defect found in this independent pass. One library deprecation warning did not affect assertions.

## Mathematical verification
Zero-rudder response equals zero-command baseline and analytic straight-line metre displacement at three headings. Positive/negative fixed rudder responses mirror east displacement, heading, ROT and actual rudder. ROT and integrated heading agree within 1e-6 with an independent piecewise-constant analytic solution using the existing right-end stepwise rudder update; this is not comparison against a different continuous-ramp model.

An isolated copied adapter changed inactive constructor placeholders from 1 to 19; full results remained identical for default, zero-speed, and negative-rudder scenarios. This tests only branches disabled by this slice, not the general vessel model.

A second isolated copied adapter sampled both trajectories at 0.05 seconds. Its actual final core state independently reproduced the published 0.1/0.05 endpoint distance, shortest heading and ROT differences within 1e-6. Step comparison is not an uncertainty interval, full error bound, real-ship calibration or accuracy certificate. No universal fourth-order claim is made.

## API and provenance
Actual API results equal standalone CLI results. Exact decimal strings preserved in canonical case/parameters/source digest: `10` versus `10.0` produce identical physics but distinct input hashes. Non-ASCII notes and source titles exercised. Numeric JSON, exponents, negative zero, leading zero, forbidden rudder/duration, and missing notes rejected instead of defaults.

Per-case minimal source snapshots; cross-case/restricted source access denied; denied roles do not learn case existence. Source/case changes after actual computation withhold output with409; revoked permission returns403. Missing executable503 with no fallback. Complete synthetic table-row snapshots unchanged by successful/no-source previews. 1000 Unicode-scalar notes accepted, 1001 rejected.

## Scope / references
Read original NomotoSimulator source, the [Nomoto/Taguchi 1957 abstract](https://www.jstage.jst.go.jp/article/jjasnaoe1952/1957/101/1957_101_57/_article/-char/en) and [ITTC 2024 revision05 manoeuvring-model validation procedure](https://www.ittc.info/media/11868/75-02-06-03.pdf). These motivate numerical and parameter documentation, not certification of this implementation.

Both tracks are hypotheses. Explicit uncalibrated active parameters and compatibility placeholders are not measured ship properties. This acceptance excludes real-ship validation, physical/model uncertainty, wind/current/bank effects, speed changes, anchors, multivessel interaction, CPA/collision/safety/avoidance/legal or causal verdicts. No W11 or real-report data involved.

## Reproduce / publish
```
cd service
MCIS_DOTNET=<existing-sdk-dotnet> DOTNET_CLI_HOME=<temporary-directory> PYTHONPATH=. .venv/bin/pytest -q ../tests_acceptance/W144/test_cli.py ../tests_acceptance/W144/test_api.py
cd ..
MCIS_DOTNET=<existing-sdk-dotnet> MCIS_BROWSER_BIN=<existing-headless-shell> python tests_acceptance/W144/browser_real.py
```
Publish only REPORT.md, test_cli.py, test_api.py, browser_real.py, server.py and verified-impl-sha256.txt. Preparatory PLAN.md, raw local-* logs and caches are not publication artifacts. Reviewer performed no deployment/publication.

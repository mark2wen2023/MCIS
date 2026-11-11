# Current CLI reproducibility and reviewed seed installation (2026-11-11 UTC)

## Scope and contract

`tools/mcis-core/build_reproducible.py` snapshots this project's csproj and all
55 explicit Compile source inputs into a temporary tree. The supported contract
is SDK 8.0.428, Release, deterministic compilation, no apphost, no Git revision
suffix, and source PathMap `/workspace/maritime-sim-design`. SDK selection is
pinned with temporary global.json (rollForward disabled). Input content and
recipe hashes, build flags, and output artifact hashes govern the cache, not
file timestamps. Evidence sources are included (the old wrapper omitted them).
Unsupported imports, resource/package/project/analyzer/target items and Compile
expressions fail closed. This is a deliberately narrow current-project contract,
not a generic complete MSBuild input resolver or SDK supply-chain attestation.

`mcis-core.sh` uses this builder. Python 3 and exact SDK 8.0.428 are prerequisites.
A stale cache, changed source/recipe, or altered artifact causes a rebuild. The
builder's output is ignored local build output, not committed binaries.

## Actual regeneration, not a hash edit

`tools/provenance/generate_seed_candidate.py` copies the needed project inputs to
an external temporary workspace and invokes the EXISTING
`python -m mcis_service.analysis.build_seed`. It eagerly builds the current CLI,
uses an isolated temporary service database, and preserves both old/new seed in
the external result folder. It never installs either into the checkout.

Verified in separate temporary roots:
- Current deterministic DLL SHA256:
  `f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf`.
- All 14,539 numeric path/value leaves exactly identical, without tolerances.
- Numeric fingerprint:
  `b1d98497ef4c5cf7181557d0481f49d484d56242b9198a5b12ae67dec723fd0e`.
- Generator's existing W14 cross-check: 52 values, max absolute difference 0.
- Exhaustive structural diff: ONLY `/generatedAt` and `/coreDll/sha256` differ.
- Original seed SHA256 remains
  `3ccc329f375de404993b65dfb1c22c3d467057bc57f376a958a22336ffb28cb5`.
- Existing production DLL remained `e24783c5…6e8d` during isolation tests.

Evidence: `current-core-seed-candidate-verification.json` includes exact candidate
hash, source/recipe/output manifest, generator hash, complete differences, and W14
cross-check. An independent reviewer reran generation in another fresh root and
confirmed the same DLL/numeric identity and unchanged checkout seed/DLL. They
also compared the 55 source paths against MSBuild evaluated Compile items exactly.

## History and review gate

The old seed and historical generating DLL remain distinct provenance records.
See `core-dll-provenance-investigation.md` and `reproduce_historical_core.py`:
the historical DLL can be reconstructed byte-for-byte, but its W3.2 Evidence
input is older than current W5.1. Do not deploy that old binary to satisfy a test.
The current seed-source assertion correctly fails while the old seed is paired
with a newer binary. No test assertion is weakened in this change.

Candidate installation was a separate review step, now completed after independent
review. The exact historical seed and original SHA sidecar were preserved at
`service/mcis_service/analysis/data/history/w12-original-20261111/`, with recovery
instructions in that directory. Both old and new evidence are retained; `generatedAt` is intentionally a real
regeneration timestamp, so entire candidate seed bytes differ between runs while
all numeric paths/values remain identical. Production source and historical
freeze manifests are not rewritten by this work.

## Reproduce

From repository root, using the service Python environment:

```sh
DOTNET_CLI_HOME=/tmp/mcis-dotnet-home service/.venv/bin/python \
  tools/provenance/generate_seed_candidate.py \
  --dotnet /tmp/mcis-dotnet/dotnet --output-dir /tmp/mcis-new-candidate-review
service/.venv/bin/python -m pytest -q tools/provenance/tests
```

Use a new external output directory each time. Nine fast helper regressions pass.
This report does not claim Unity, mobile, deployment, or full system acceptance.

Additional isolated acceptance: the unchanged existing
`service/tests/test_analysis_w12.py` ran against a genuinely regenerated seed and
current deterministic DLL in the isolated project copy: **16 passed in 7.50s**,
including `test_seed_sources_not_stale`. This result does not imply the checkout's
not-yet-installed candidate is already active.

## Reviewed installation (after the isolation results above)

Following the parent review gate, the exact candidate was installed, not edited:
`988e9abd3b39959864f42912d8d3454dacd7821156fd8b21268631f30f4693e3`.
The new wrapper rebuilt the current production output to the expected
`f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf`.
`logs/current-core-installed-provenance.json` records the active and archived
identities. Runtime `version` succeeded; output is in `current-core-version.json`.
The earlier statements that checkout data was untouched refer to the isolation
phase only; this section records the subsequent authorized installation.

Frontend report rendering passed 148 assertions (`current-core-report-web-test.txt`).
An initial combined W12/provenance run produced 29 passes and one outdated UI
source-string assertion failure, unrelated to numeric provenance. The independent
UI reviewer is updating that architecture assertion to the current case-context
contract without weakening its analysis-only fallback requirement.

### Final installed-baseline checks

- Combined unchanged numeric W12 checks plus provenance helpers: **30 passed**
  (`current-core-w12-provenance-final-pytest.txt`), after the independent UI
  reviewer updated the obsolete source-string architecture assertion.
- Independent W12 rerun: **21 passed** (`current-w12-independent-retest.txt`).
- The first full service run had **315 passed, 1 failed**. The sole failure was
  `test_custody_jsonl_accepted_by_csharp_ledger`: the existing mcis-compat launcher
  reads `DOTNET_ROOT`, not `MCIS_DOTNET`, and defaulted to an absent SDK. Both the
  first run and targeted diagnostic are retained. No assertion was changed to
  hide that failure. The complete rerun sets both documented SDK environment
  variables (result recorded below when finished).

Full service reproduction (from repository root):

```sh
cd service
DOTNET_ROOT=/tmp/mcis-dotnet MCIS_DOTNET=/tmp/mcis-dotnet/dotnet \
  DOTNET_CLI_HOME=/tmp/mcis-dotnet-home .venv/bin/python -m pytest -q
```

These SDK paths are local examples: substitute the installed official SDK path.
Binary reproducibility was established on the current Linux environment with
SDK 8.0.428 under multiple different temporary source-root paths. It is **not** a
claim of byte equality across operating systems, architectures, or SDK versions.

**Final full service rerun: 316 passed in 131.91 seconds**, exit 0, with
`DOTNET_ROOT` and `MCIS_DOTNET` configured for the same SDK. See
`current-core-service-configured-pytest.txt`. This includes the original seed
freshness, report source/export, custody compatibility, and all service tests;
no numerical or source-freshness assertion was weakened. First-run failure logs
remain for transparency.

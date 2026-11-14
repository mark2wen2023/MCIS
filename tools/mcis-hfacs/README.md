# W18.4 project HFACS classification draft CLI

Run tools/mcis-hfacs/mcis-hfacs.sh with JSON stdin and no arguments. Existing
.NET SDK8.0.428/Python3 required; MCIS_DOTNET selects dotnet. Contract:
contracts/hfacs-draft-v1.md. No external calls or business-data persistence.

Actions: {"action":"taxonomy"} and {"action":"validate","draft":...}.
Taxonomy comes directly from HfacsMaTaxonomy.All; 32 categories,5 roots, original
names/codes/layer names, null parent for roots, isLeaf via ChildrenOf. This is
project-specific maritime-adapted taxonomy requiring expert review, not an
official universal classification standard. Category titles are not allegations.

Each validation uses a fresh HfacsAnalysis and original AddFinding. Root/group
and leaf categories accepted for ToBeVerified. All entries fixed Draft,
ToBeVerified,Investigator; evidence/ECFC arrays empty, ledger null. No Confirm or
Reject call. Unknown category/duplicate ID invalidates entire batch (no partial
result). Description/rationale/scope protocol constraints are adapter checks;
rationale meaning and description truth are not classified or verified by core.
Layer/category results do not establish causality, responsibility or facts.

The backend owns source metadata binding, transaction, saved-draft revision,
authorization and audit. AddFinding does not emit save audit. This tool neither
confirms nor persists drafts. No W11 source or adapter is referenced.

Explicit seven unchanged core/domain sources compile in isolated locked builds.
build-manifest.json records source/artifact hashes. Generated out/ is not for
publication. Protocol/core failures exit4, operational failures nonzero; build
failures can produce no JSON. Never treat absent output as successful validation.

Run synthetic tests: python tools/mcis-hfacs/test_cli.py with SDK environment.
Concurrent rebuild test invalidates adapter receipt; run while adapter idle.

## Environment diagnosis (no substitute classification)

From the repository root run `python3 tools/mcis-hfacs/check_environment.py`.
This invokes only the configured dotnet `--version` (5 second timeout), never
builds, installs, calls a model or changes fixtures. It uses the build recipe's
SDK pin and source list. It does not print configured paths, process output or
environment values. Exit 1 identifies missing/unusable/wrong SDK or missing
sources; exit 0 means prerequisites ready to **attempt** a build, not HFACS
validation success. DLL/manifest presence is not integrity verification.
The configured runtime may perform its own normal initialization.

The wrapper uses `MCIS_DOTNET`, otherwise `$HOME/.dotnet/dotnet`; a dotnet on PATH
alone does not override that default. A missing DLL is expected before the first
successful build and must not be replaced with a copied/unverified binary.
Have the environment owner provision the genuine .NET SDK **8.0.428**, configure
MCIS_DOTNET if needed, then run the checker and the real adapter:

```sh
printf '%s\n' '{"action":"taxonomy"}' | bash tools/mcis-hfacs/mcis-hfacs.sh
python3 tools/mcis-hfacs/test_cli.py
service/.venv/bin/pytest -q service/tests/test_track_history.py::test_real_hfacs_and_report_optional_extension_three_generations service/tests/test_working_record_archive.py::test_report_versions_full_review_gisis_and_hfacs_coexist
```

The actual build verifies source/artifact receipts; these later commands are
required to establish real core and archive workflow behavior. The diagnostic
unit tests use process doubles and do not establish .NET/core correctness.
Without the real core, service HTTP 503 `HFACS_CORE_UNAVAILABLE` remains the safe
behavior. No fallback taxonomy, validation, successful archive assertion or
automatic skip is supplied. These two scenarios exercise HFACS coexistence;
their environment failure does not establish all other suite failures are
environmental. Genuine SDK/build/protocol failures still require investigation.

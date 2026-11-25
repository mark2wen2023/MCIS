# W17 custody JSONL interoperability (.NET 8, offline)

Product source: `d40e3b5fd2e208af84c84d6faf61095d0a0a89fb`. This gate uses
the existing McisCompat console program and original Unity-domain C# reader,
not the Unity runtime. It depends on the sibling `w17-restart-reexport`
acceptance helper and pin manifest at their fixed contents. No source is
modified, no downloaded packages are used, and disposable outputs are removed.

On a pre-equipped Linux runner, set PYTHON to the existing MCIS Python
virtual-environment executable and DOTNET to an installed .NET 8 SDK host
with .NET 8 runtime and local SDK targeting/reference packs. Set ACCEPTANCE
to the directory containing this README. From a Git checkout already holding
the exact commit:

```sh
set -eu
SOURCE="$(mktemp -d)"
trap 'rm -rf -- "$SOURCE"' EXIT
git archive --format=tar d40e3b5fd2e208af84c84d6faf61095d0a0a89fb \
  service contracts tools/mcis-compat \
  unity/Assets/_Project/Scripts/Core/Primitives \
  unity/Assets/_Project/Scripts/Domain/Evidence > "$SOURCE/source.tar"
tar -xf "$SOURCE/source.tar" -C "$SOURCE"
"$PYTHON" -I -B "$ACCEPTANCE/run.py" --source "$SOURCE" --dotnet "$DOTNET"
```

Run on an offline/egress-disabled machine. The existing project has no
PackageReference, ProjectReference, or non-SDK imports. The runner restores
using a temporary empty package cache with all package/fallback/audit sources
cleared, then builds with --no-restore. If installed targeting/reference packs
do not suffice, record failure; don't connect an external feed. --pins-only
checks the 190 backend/contract and 9 C# file hashes without running .NET.

Expected evidence: SDK/runtimes shown; private localhost-only FastAPI creates
an unseeded synthetic case, one restricted item with an escaped multilingual
review reason and one separately verified item. Export must be HTTP 200,
application/zip, no-store, format 1.4.0 before invoking C#. Pass the untouched
audit/custody.jsonl member to the freshly compiled existing reader. Require
rc 0, 4 events, 2 items, NeedsReview and Verified on the correct IDs, exactly
one restricted ID, and a printed custody SHA-256. The existing reader enforces
ordinal equality to CustodyEvent.ToJsonLine for every row after parsing and
validates the previous-line hash chain. An isolated noncanonical final row
must produce rc 1 with custody_chain_broken. This is not a Unity scene,
production identity check, browser replay, or broad archive validation.

Local verification: 199 pins and missing-SDK fail-closed path checked on
2026-11-25. No usable SDK/runtime seen. Build, offline restore, HTTP→C#
interop and exact final-row rejection remain to be run on a pre-equipped host.

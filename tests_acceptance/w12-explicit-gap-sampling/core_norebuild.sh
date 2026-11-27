#!/usr/bin/env bash
# Run an already-built official mcis-core DLL. Never rebuild, never call NuGet.
set -euo pipefail
DOTNET="${MCIS_DOTNET:-$HOME/.dotnet/dotnet}"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 DOTNET_ROOT="$(dirname "$DOTNET")"
DLL="${MCIS_CORE_DLL:?MCIS_CORE_DLL must point at the locked official mcis-core.dll}"
exec "$DOTNET" "$DLL" "$@"

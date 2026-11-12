#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DOTNET="${MCIS_DOTNET:-$HOME/.dotnet/dotnet}"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 DOTNET_ROOT="$(dirname "$DOTNET")"
python3 "$HERE/build.py"
exec "$DOTNET" "$HERE/out/mcis-rest.dll"

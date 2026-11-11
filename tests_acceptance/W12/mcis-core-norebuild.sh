#!/usr/bin/env bash
# W12 independent acceptance: run an already-built real CLI, never rebuild it here.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DOTNET="${MCIS_DOTNET:-$HOME/.dotnet/dotnet}"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 DOTNET_ROOT="$(dirname "$DOTNET")"
exec "$DOTNET" "$ROOT/tools/mcis-core/out/mcis-core.dll" "$@"

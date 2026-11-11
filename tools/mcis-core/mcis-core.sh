#!/usr/bin/env bash
# mcis-core 启动包装：首次或源码更新后自动构建，然后以 stdin/stdout JSON 运行。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DOTNET="${MCIS_DOTNET:-$HOME/.dotnet/dotnet}"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 DOTNET_ROOT="$(dirname "$DOTNET")"
DLL="$HERE/out/mcis-core.dll"
# Hash all csproj Compile inputs (including Evidence); timestamps are not provenance.
python3 "$HERE/build_reproducible.py" --dotnet "$DOTNET" --output "$HERE/out"
exec "$DOTNET" "$DLL" "$@"

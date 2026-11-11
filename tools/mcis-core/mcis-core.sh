#!/usr/bin/env bash
# mcis-core 启动包装：首次或源码更新后自动构建，然后以 stdin/stdout JSON 运行。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DOTNET="${MCIS_DOTNET:-$HOME/.dotnet/dotnet}"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 DOTNET_ROOT="$(dirname "$DOTNET")"
DLL="$HERE/out/mcis-core.dll"
SCRIPTS="$HERE/../../unity/Assets/_Project/Scripts"
# src/csproj 或已接入的计算源码更新后重编（含 W2 Timeline/Vdr）。
if [[ ! -f "$DLL" || -n "$(find "$HERE/src" "$HERE/McisCore.csproj"     "$SCRIPTS/Core/Primitives" "$SCRIPTS/Domain/Common" "$SCRIPTS/Domain/Models"     "$SCRIPTS/Domain/Geo" "$SCRIPTS/Domain/Cpa" "$SCRIPTS/Domain/Colreg" "$SCRIPTS/Domain/Timeline" "$SCRIPTS/Data/Vdr"     -newer "$DLL" 2>/dev/null | head -1)" ]]; then
  "$DOTNET" build "$HERE/McisCore.csproj" -c Release -o "$HERE/out" >&2
fi
exec "$DOTNET" "$DLL" "$@"

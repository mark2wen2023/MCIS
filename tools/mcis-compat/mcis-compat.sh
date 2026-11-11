#!/usr/bin/env bash
# 测试用：构建并运行 mcis-compat（引用 unity/ 下只读 C# 源）。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.dotnet}"
DOTNET="$DOTNET_ROOT/dotnet"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
OUT="$HERE/out/mcis-compat.dll"
if [[ ! -f "$OUT" ]] || [[ -n "$(find "$HERE/src" "$HERE/McisCompat.csproj" "$HERE/../../unity/Assets/_Project/Scripts/Domain/Evidence" "$HERE/../../unity/Assets/_Project/Scripts/Core/Primitives" -newer "$OUT" -name '*.cs*' -print -quit)" ]]; then
  "$DOTNET" build "$HERE/McisCompat.csproj" -c Release -o "$HERE/out" -nologo -v q >&2
fi
exec "$DOTNET" "$OUT" "$@"

#!/usr/bin/env bash
# W6验收：只执行预构建的真实CLI，路径相对仓库；不自动构建或替换计算结果。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DOTNET="${MCIS_DOTNET:-$HOME/.dotnet/dotnet}"
DLL="${MCIS_CORE_DLL:-$ROOT/tools/mcis-core/out/mcis-core.dll}"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
export DOTNET_ROOT="$(dirname "$DOTNET")"
exec "$DOTNET" "$DLL" "$@"

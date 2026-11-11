#!/usr/bin/env bash
# W6 验收用：直接运行已构建的 mcis-core.dll，不触发重编（避免与其它包并行构建冲突）
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 DOTNET_ROOT="$HOME/.dotnet"
exec "$HOME/.dotnet/dotnet" /workspace/maritime-sim-design/tools/mcis-core/out/mcis-core.dll "$@"

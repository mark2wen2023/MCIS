#!/bin/bash
set -euo pipefail
export HOME=/home/box
export DOTNET_CLI_TELEMETRY_OPTOUT=1
export DOTNET_NOLOGO=1
export DOTNET_ROOT=/home/box/.dotnet
# do not invent DOTNET_CLI_HOME; keep initialized login HOME
unset DOTNET_CLI_HOME || true
PATH="/home/box/.dotnet:$PATH"

echo "=== isolation preflight ==="
date '+%Y-%m-%d %H:%M:%S %Z'
echo "HOME=$HOME"
echo "DOTNET_CLI_HOME=${DOTNET_CLI_HOME-<unset>}"
ip -o link show
ip -4 addr show
echo "--- resolve ---"
getent hosts 127.0.0.1 || true
getent hosts nuget.org || echo "nuget.org: UNRESOLVED (expected)"
getent hosts api.nuget.org || echo "api.nuget.org: UNRESOLVED (expected)"
# confirm no default route / no other ifaces with addresses besides lo
echo "--- routes ---"
ip route || true

echo "=== SDK preflight ==="
/home/box/.dotnet/dotnet --version
/home/box/.dotnet/dotnet --list-sdks
echo "=== NuGet locals (do not skip) ==="
/home/box/.dotnet/dotnet nuget locals all --list

echo "=== official reproducible build ==="
# empty output already prepared; official recipe from the clean export
/usr/bin/python3 /workspace/mcis-w41-src-94d5e38/tools/mcis-core/build_reproducible.py \
  --dotnet /home/box/.dotnet/dotnet \
  --output /workspace/mcis-w41-core-out
echo "BUILD_EXIT=$?"

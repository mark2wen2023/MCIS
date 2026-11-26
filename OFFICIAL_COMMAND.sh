#!/bin/bash
set -u
export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-C.UTF-8}"
export PATH="/home/box/.dotnet:/usr/bin:/bin:${PATH:-/usr/bin:/bin}"
REPORT="/workspace/mcis-w11-revoke-control-report"
PY="/workspace/mcis-w17-871db66/service/.venv/bin/python"
DOTNET="/home/box/.dotnet/dotnet"
RUN="/workspace/mcis-w11-isolated-cand/tests_acceptance/w11-isolated-synthetic-pilot/revoke_control.py"
/usr/bin/timeout --signal=TERM --kill-after=10s 150s /usr/bin/unshare -r -n /bin/bash -c '
  set -euo pipefail
  ip link set lo up
  exec "$0" -I -B "$1" --dotnet "$2" --python "$0" --report "$3"
' "$PY" "$RUN" "$DOTNET" "$REPORT"

#!/bin/bash
set -u
export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-C.UTF-8}"
export PATH="/usr/bin:/bin:${PATH:-/usr/bin:/bin}"
REPORT="/workspace/mcis-w19-keyword-control-report"
PY="/workspace/mcis-w17-871db66/service/.venv/bin/python"
RUN="/workspace/mcis-w19-retrieval-cand/tests_acceptance/w19-knowledge-card-retrieval/keyword_control.py"
/usr/bin/timeout --signal=TERM --kill-after=10s 150s /usr/bin/unshare -r -n /bin/bash -c '
  set -euo pipefail
  ip link set lo up
  exec "$0" -I -B "$1" --python "$0" --report "$2"
' "$PY" "$RUN" "$REPORT"

#!/bin/bash
set -u
export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-C.UTF-8}"
export PATH="/usr/bin:/bin:${PATH:-/usr/bin:/bin}"
unset MCIS_API HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY
exec /usr/bin/timeout --signal=TERM --kill-after=10s 150s /usr/bin/unshare -r -n /bin/bash -c '
  /usr/bin/ip link set lo up
  exec /workspace/mcis-w17-871db66/service/.venv/bin/python -I -B \
    /workspace/mcis-w12-gap-cand/tests_acceptance/w12-explicit-gap-sampling/run.py \
    --worktree /workspace/mcis-w12-gap-cand \
    --report /workspace/mcis-w12-explicit-gap-report \
    --core-dir /workspace/mcis-w41-core-out \
    --dotnet /home/box/.dotnet/dotnet \
    --host 127.0.0.1 \
    --port 18775
'

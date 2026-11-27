#!/bin/bash
set -u
export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-C.UTF-8}"
export PATH="/usr/bin:/bin:${PATH:-/usr/bin:/bin}"
unset MCIS_API HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY
# Browser official run: do not combine Chrome with unshare -r. Loopback only. 150s outer timeout.
exec /usr/bin/timeout --signal=TERM --kill-after=10s 150s \
  /workspace/w17-pyplaywright-venv/bin/python -I -B \
  /workspace/mcis-w12-chart-cand/tests_acceptance/w12-chart-explicit-gap/run.py \
  --python /workspace/mcis-w17-871db66/service/.venv/bin/python \
  --report /workspace/mcis-w12-chart-gap-report \
  --worktree /workspace/mcis-w12-chart-cand \
  --browser /opt/google/chrome/chrome \
  --port 18776

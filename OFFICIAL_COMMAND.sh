#!/bin/bash
# After-state official measurement (before was captured on the unmodified 03a8e786 dist).
set -u
export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-C.UTF-8}"
export PATH="/usr/bin:/bin:${PATH:-/usr/bin:/bin}"
unset MCIS_API HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY
exec /usr/bin/timeout --signal=TERM --kill-after=10s 150s \
  /workspace/w17-pyplaywright-venv/bin/python -I -B \
  /workspace/mcis-w12-narrow-cand/tests_acceptance/w12-narrow-layout/measure.py \
  --python /workspace/mcis-w17-871db66/service/.venv/bin/python \
  --report /workspace/mcis-w12-narrow-layout-report \
  --worktree /workspace/mcis-w12-narrow-cand \
  --browser /opt/google/chrome/chrome \
  --port 18773 \
  --label after \
  --also-desktop \
  --keyboard

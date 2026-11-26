#!/bin/bash
set -u
export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-C.UTF-8}"
export PATH="/usr/bin:/bin:${PATH:-/usr/bin:/bin}"
unset MCIS_API HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY
# Do not use unshare: a nested user namespace can break the Chrome sandbox,
# and --no-sandbox is forbidden. Service and browser are loopback-only.
exec /usr/bin/timeout --signal=TERM --kill-after=10s 150s \
  /workspace/w17-pyplaywright-venv/bin/python -I -B \
  /workspace/mcis-w12-scope-cand/tests_acceptance/w12-snapshot-scope-browser/run.py \
  --python /workspace/mcis-w17-871db66/service/.venv/bin/python \
  --report /workspace/mcis-w12-snapshot-scope-report \
  --worktree /workspace/mcis-w12-scope-cand \
  --browser /opt/google/chrome/chrome \
  --port 18770 \
  --viewport desktop \
  --also-390

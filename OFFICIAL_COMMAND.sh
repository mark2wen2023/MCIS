#!/bin/bash
set -u
export LANG="${LANG:-C.UTF-8}"
export LC_ALL="${LC_ALL:-C.UTF-8}"
cd /workspace/mcis-w19-page-search-cand
exec /usr/bin/timeout --signal=TERM --kill-after=10s 150s env \
  MCIS_HOST_PYTHON=/workspace/mcis-w17-871db66/service/.venv/bin/python \
  MCIS_CHROMIUM=/opt/google/chrome/google-chrome \
  MCIS_NODE_MODULES=/workspace/mcis-w17-871db66/web/node_modules \
  MCIS_BROWSER_EVIDENCE_DIR=/workspace/mcis-w19-page-search-report/official-evidence \
  /workspace/w17-pyplaywright-venv/bin/python tests_acceptance/w19-page-search/run.py

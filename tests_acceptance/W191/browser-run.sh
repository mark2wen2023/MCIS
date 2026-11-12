#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
: "${W191_PLAYWRIGHT:?Set path to Playwright module}"
: "${W191_CHROMIUM:?Set path to Chromium executable}"
export W191_API_PORT=${W191_API_PORT:-18219} W191_WEB_PORT=${W191_WEB_PORT:-16219}
export W191_TMP=$(mktemp -d) W191_ROOT=$ROOT
cd "$ROOT"
service/.venv/bin/python - <<'PY' >"$W191_TMP/service.log" 2>&1 &
import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(os.environ['W191_ROOT'])/'service'))
from mcis_service.main import create_app
from mcis_service.config import Settings
import uvicorn
uvicorn.run(create_app(Settings(data_dir=Path(os.environ['W191_TMP'])/'data',seed_demo=True)),host='127.0.0.1',port=int(os.environ['W191_API_PORT']),log_level='warning')
PY
A=$!
(cd web && MCIS_API=http://127.0.0.1:$W191_API_PORT exec node node_modules/vite/bin/vite.js --host 127.0.0.1 --port "$W191_WEB_PORT" --strictPort) >"$W191_TMP/vite.log" 2>&1 &
B=$!
trap 'kill "$A" "$B" 2>/dev/null || true; wait "$A" "$B" 2>/dev/null || true' EXIT
for i in $(seq 1 80); do curl -fs "http://127.0.0.1:$W191_API_PORT/api/v1/health" >/dev/null && curl -fs "http://127.0.0.1:$W191_WEB_PORT" >/dev/null && break; sleep .25; done
node tests_acceptance/W191/browser.cjs

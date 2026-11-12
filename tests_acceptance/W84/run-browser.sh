#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
PYTHON=${MCIS_PYTHON:-"$ROOT/service/.venv/bin/python"}
export MCIS_W84_RUN_DIR=$(mktemp -d "${TMPDIR:-/tmp}/mcis-w84-acceptance.XXXXXX")
A= B=
cleanup() { test -z "$A" || kill "$A" 2>/dev/null || true; test -z "$B" || kill "$B" 2>/dev/null || true; }
trap cleanup EXIT
"$PYTHON" "$ROOT/tests_acceptance/W84/fixture_server.py" >"$MCIS_W84_RUN_DIR/api.log" 2>&1 & A=$!
for i in $(seq 1 60); do test -f "$MCIS_W84_RUN_DIR/session.json" && break; sleep .25; done
API=$("$PYTHON" -c 'import json,os;print(json.load(open(os.path.join(os.environ["MCIS_W84_RUN_DIR"],"session.json")))["api"])')
PORT=$("$PYTHON" -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')
export MCIS_W84_WEB_URL="http://127.0.0.1:$PORT"
(cd "$ROOT/web" && MCIS_API="$API" exec node node_modules/vite/bin/vite.js --host 127.0.0.1 --port "$PORT" --strictPort) >"$MCIS_W84_RUN_DIR/vite.log" 2>&1 & B=$!
for i in $(seq 1 60); do curl -fs "$MCIS_W84_WEB_URL" >/dev/null && break; sleep .25; done
node "$ROOT/tests_acceptance/W84/${MCIS_W84_BROWSER_SCRIPT:-browser.cjs}"

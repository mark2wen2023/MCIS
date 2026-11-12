#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PY="$ROOT/service/.venv/bin/python"
if [[ ! -x "$PY" ]]; then echo 'Existing service/.venv Python required; no dependency installation performed.' >&2; exit 2; fi
exec "$PY" "$ROOT/tools/stage-demo/run.py" "$@"

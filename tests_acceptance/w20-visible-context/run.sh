#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
WEB="${2:-$ROOT/web}"
SERVICE="${3:-$ROOT/service}"
PY="${MCIS_HOST_PYTHON:-python3}"
: "${MCIS_HAPPY_DOM_PATH:?Set MCIS_HAPPY_DOM_PATH to the existing absolute happy-dom/lib/index.js}"
: "${MCIS_NODE_MODULES:=$WEB/node_modules}"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
cp -r "$WEB/src" "$TMP/src"
cp "$ROOT/web/src/agents/AgentReviewPanel.tsx" "$TMP/src/agents/"
mkdir "$TMP/tests"
cp "$ROOT/web/tests/agent-review-visible-context.test.tsx" "$TMP/tests/"
ln -s "$MCIS_NODE_MODULES" "$TMP/node_modules"
"$TMP/node_modules/.bin/esbuild" "$TMP/tests/agent-review-visible-context.test.tsx" \
  --bundle --platform=node --format=cjs --jsx=automatic --alias:happy-dom="$MCIS_HAPPY_DOM_PATH" \
  --loader:.css=empty --outfile="$TMP/run.cjs" --log-level=warning
node "$TMP/run.cjs"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$SERVICE" "$PY" "$ROOT/tests_acceptance/w20-visible-context/check_service.py"

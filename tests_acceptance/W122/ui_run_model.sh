#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
OUT=$(mktemp /tmp/w122-ui-model-XXXXXX.cjs)
trap 'rm -f "$OUT"' EXIT
NODE_PATH="$ROOT/web/node_modules" ./web/node_modules/.bin/esbuild tests_acceptance/W122/ui_model.test.tsx --bundle --platform=node --format=cjs --outfile="$OUT" --jsx=automatic --loader:.css=empty --log-level=warning
node -e 'global.localStorage={getItem:()=>null};require(process.argv[1])' "$OUT"

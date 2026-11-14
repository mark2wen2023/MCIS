#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WEB="$(cd "$HERE/../.." && pwd)"
NODE_PATH="$HERE/node_modules" "$WEB/node_modules/.bin/esbuild" \
  "$WEB/tests/registered-independent.tsx" --bundle --platform=node --format=esm \
  --outfile="$WEB/tests/.tmp-registered-independent.mjs" --jsx=automatic \
  --loader:.css=empty \
  --banner:js='import { createRequire } from "node:module"; const require = createRequire(import.meta.url);' \
  --log-level=warning
node "$WEB/tests/.tmp-registered-independent.mjs"

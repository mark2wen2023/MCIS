#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
npx esbuild tests/access-workbench-w171.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-access-workbench-w171.cjs --jsx=automatic --log-level=warning
node tests/.tmp-access-workbench-w171.cjs

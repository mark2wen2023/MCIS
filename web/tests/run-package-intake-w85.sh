#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
npx esbuild tests/package-intake-w85.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-package-intake-w85.cjs --jsx=automatic --log-level=warning
node tests/.tmp-package-intake-w85.cjs

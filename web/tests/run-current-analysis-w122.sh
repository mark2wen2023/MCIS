#!/usr/bin/env bash
set -euo pipefail
npx esbuild tests/current-analysis-w122.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-current-analysis-w122.cjs --jsx=automatic --log-level=warning
node tests/.tmp-current-analysis-w122.cjs

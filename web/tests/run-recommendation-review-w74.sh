#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
node_modules/.bin/esbuild tests/recommendation-review-w74.test.ts --bundle --platform=node --format=cjs --outfile=tests/.tmp-recommendation-review-w74.cjs --log-level=warning
node tests/.tmp-recommendation-review-w74.cjs

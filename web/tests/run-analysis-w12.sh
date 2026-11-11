#!/bin/bash
# W12 前端用例（不改 package.json：W6.1 冻结期内 package.json 在冻结清单里）。在 web/ 下运行：bash tests/run-analysis-w12.sh
set -euo pipefail
cd "$(dirname "$0")/.."
npx esbuild tests/analysis-w12.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-analysis-w12.cjs --jsx=automatic --loader:.css=empty --log-level=warning
node tests/.tmp-analysis-w12.cjs

#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
web/node_modules/.bin/esbuild tests_acceptance/PUBLICREPORTTEXT/independent.test.tsx --bundle --platform=node --format=esm --outfile=tests_acceptance/PUBLICREPORTTEXT/.tmp-independent.mjs --jsx=automatic --loader:.css=empty --alias:react=./web/node_modules/react --alias:react-dom=./web/node_modules/react-dom --external:/tmp/mcis-ui-deps/node_modules/happy-dom/lib/index.js --log-level=warning
node tests_acceptance/PUBLICREPORTTEXT/.tmp-independent.mjs

#!/usr/bin/env sh
# Deterministic ECFC auto-layout regression plus the existing ECFC model suite. No network, no install.
set -eu
cd "$(dirname "$0")/.."
./node_modules/.bin/esbuild tests/ecfc-auto-layout.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-ecfc-auto-layout.cjs --jsx=automatic --log-level=warning
node tests/.tmp-ecfc-auto-layout.cjs
./node_modules/.bin/esbuild tests/ecfc-model.test.tsx --bundle --platform=node --format=cjs --outfile=tests/.tmp-ecfc-model.cjs --jsx=automatic --log-level=warning
node tests/.tmp-ecfc-model.cjs
rm -f tests/.tmp-ecfc-auto-layout.cjs tests/.tmp-ecfc-model.cjs

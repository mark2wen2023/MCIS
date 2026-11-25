#!/usr/bin/env bash
set -euo pipefail
# Inputs are exact fixed sources plus already installed dependencies.
here="$(cd "$(dirname "$0")" && pwd)"
: "${MCIS_FIXED_SERVICE:?fixed service root}" "${MCIS_FIXED_WEB:?fixed web root}" "${MCIS_W11_SYNTHETIC_ORIGINAL:?fixed synthetic original}"
: "${MCIS_NODE_MODULES:?installed dependencies}" "${MCIS_HOST_PYTHON:?installed service Python}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/src"
cp -r "$MCIS_FIXED_WEB/src/ecfcDrafts" "$tmp/src/"
cp "$here/edge-host.test.tsx" "$tmp/"
ln -s "$MCIS_NODE_MODULES" "$tmp/node_modules"
# Never import the pilot or build the mounted view from an unexpected baseline.
"$MCIS_HOST_PYTHON" -I -B - "$here" "$MCIS_FIXED_WEB" "$MCIS_FIXED_SERVICE" <<'PINS'
from pathlib import Path
from hashlib import sha1
import sys
here,web,service = map(Path,sys.argv[1:])
pins = {
 here.parent/'w11-excerpt-binding-local/check.py':'0f77b3626fefe20fd0fed7b3b6ea72f928610a56',
 here.parent/'w11-excerpt-binding-local/pilot.py':'78c44747d6709ec5142aa413f167866c1f7d70f4',
 web/'src/ecfcDrafts/EdgeSelection.tsx':'23b43a697ada26a87a5f5a7a418c59356aa07db6',
 web/'src/ecfcDrafts/Graph.tsx':'7a68c9cb721a265b1c67c940044288daee77c52c',
 web/'src/ecfcDrafts/model.ts':'aee50d3472990fdc69aed5ea8e33c78938db66ac',
 service/'mcis_service/ecfc_drafts/router.py':'fc432a2934a6748f5f7cc6e87e9bbf28b50c8745',
 service/'mcis_service/ecfc_drafts/models.py':'da82b921f8ab92e2473ff32f7b36fb472fa8a656',
 service/'mcis_service/evidence_intake/router.py':'9be3be4a060ed62ccda68c9371fe48280a5afa43',
}
for path,pin in pins.items():
    data=path.read_bytes()
    assert sha1(b'blob '+str(len(data)).encode()+b"\0"+data).hexdigest()==pin,path
PINS
cd "$tmp"
if [[ "${1:-}" == "--browser" ]]; then
 : "${MCIS_BROWSER_BIN:?existing sandboxed Chromium}" "${MCIS_BROWSER_PYTHON:?existing Python with Playwright}" "${MCIS_W11_BROWSER_OUT:?absolute output directory}"
 mkdir -p "$MCIS_W11_BROWSER_OUT"
 if [[ -n "$(ls -A "$MCIS_W11_BROWSER_OUT")" ]]; then echo "Browser output directory must be empty" >&2; exit 2; fi
 cp "$here/browser-entry.tsx" .
 "$MCIS_NODE_MODULES/.bin/esbuild" browser-entry.tsx --bundle --platform=browser --format=iife --jsx=automatic \
   --loader:.css=empty --outfile=app.js --log-level=warning
 export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$MCIS_FIXED_SERVICE"
 set +e
 "$MCIS_BROWSER_PYTHON" -B "$here/browser_check.py" "$MCIS_HOST_PYTHON" "$MCIS_W11_SYNTHETIC_ORIGINAL" "$tmp" "$MCIS_BROWSER_BIN" "$MCIS_W11_BROWSER_OUT" >"$MCIS_W11_BROWSER_OUT/run.log" 2>&1
 status=$?
 set -e
 printf '%s\n' "$status" >"$MCIS_W11_BROWSER_OUT/exit-code.txt"
 cat "$MCIS_W11_BROWSER_OUT/run.log"
 exit "$status"
fi
: "${MCIS_HAPPY_DOM_PATH:?installed happy-dom entry}"
"$MCIS_NODE_MODULES/.bin/esbuild" edge-host.test.tsx --bundle --platform=node --format=cjs --jsx=automatic \
  --alias:happy-dom="$MCIS_HAPPY_DOM_PATH" --loader:.css=empty --outfile=check.cjs --log-level=warning
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$MCIS_FIXED_SERVICE"
for action in revised revoke; do
 mkdir "$tmp/$action"
 node check.cjs "$MCIS_HOST_PYTHON" "$here/host.py" "$MCIS_W11_SYNTHETIC_ORIGINAL" "$tmp/$action" "$action"
done

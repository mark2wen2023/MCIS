#!/bin/bash
# SVG → PNG（无头 Chrome）。用法: ./render.sh name.svg W H scale
cd "$(dirname "$0")"
f=$1; w=$2; h=$3; s=${4:-2}
base=${f%.svg}
cat > /tmp/_wrap.html <<HTML
<html><body style="margin:0;background:#040910"><img src="file://$PWD/$f" width="$w" height="$h" style="display:block"></body></html>
HTML
google-chrome --headless=new --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=$s \
  --window-size=$w,$h --virtual-time-budget=2000 --screenshot="$PWD/${base}.png" file:///tmp/_wrap.html >/dev/null 2>&1
echo "$PWD/${base}.png"

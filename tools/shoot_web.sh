#!/bin/bash
# 无头 Chrome 1440×900 截图：Web 工作台两张已接后端的页面（需先 ./run_dev.sh --preview）。
cd "$(dirname "$0")/.."
OUT=screenshots/1440
BASE="${WEB_BASE:-http://127.0.0.1:4173}"
mkdir -p "$OUT"
for r in evidence recs; do
  f="$OUT/20-${r}-1440.png"
  google-chrome --headless=new --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --window-size=1440,900 --virtual-time-budget=8000 \
    --screenshot="$f" "$BASE/#/${r}" >/dev/null 2>&1
  echo "$f"
done

#!/bin/bash
# 无头 Chrome 截图：W6 避碰规则对照页（Lily/Mary 与 海力5，1440×900 与 1920×1080）。
# 需先启动后端与前端（默认预览 http://127.0.0.1:4173）。
set -euo pipefail
cd "$(dirname "$0")/.."
BASE="${WEB_BASE:-http://127.0.0.1:4173}"
HAILI="CASE-2025-HAILI5-WANA17"
CHROME=(google-chrome --headless=new --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --virtual-time-budget=12000)
mkdir -p screenshots/1440

shot() {
  local w="$1" h="$2" out="$3" url="$4"
  "${CHROME[@]}" --window-size="$w,$h" --screenshot="$out" "$url" >/dev/null 2>&1
  echo "$out ($(wc -c < "$out") bytes)"
}

shot 1440 900 screenshots/1440/20-colreg-1440.png "$BASE/#/colreg"
shot 1920 1080 screenshots/20-colreg.png "$BASE/#/colreg"
shot 1440 900 screenshots/1440/20-colreg-haili5-1440.png "$BASE/#/colreg?case=$HAILI"
shot 1920 1080 screenshots/20-colreg-haili5.png "$BASE/#/colreg?case=$HAILI"

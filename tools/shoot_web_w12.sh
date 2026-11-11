#!/bin/bash
# 无头 Chrome 截图：W12 分析页（Lily/Mary、海力5、YANGZE 22；1440×900 与 1920×1080，另附整页长图）。
# 需先启动后端与前端；默认用临时预览端口（不碰 8765/4173）：WEB_BASE=http://127.0.0.1:14173
set -euo pipefail
cd "$(dirname "$0")/.."
BASE="${WEB_BASE:-http://127.0.0.1:14173}"
HAILI="CASE-2025-HAILI5-WANA17"
YANGZE="CJK-2024-1230-YangZe22-VegaDream"
CHROME=(google-chrome --headless=new --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --virtual-time-budget=12000)
mkdir -p screenshots/1440

shot() {
  local w="$1" h="$2" out="$3" url="$4"
  "${CHROME[@]}" --window-size="$w,$h" --screenshot="$out" "$url" >/dev/null 2>&1
  echo "$out ($(wc -c < "$out") bytes)"
}

for spec in "lily-mary|" "haili5|?case=$HAILI" "yangze22|?case=$YANGZE&scenario=Y1"; do
  key="${spec%%|*}"; q="${spec#*|}"
  shot 1440 900  "screenshots/1440/30-analysis-$key-1440.png" "$BASE/#/analysis$q"
  shot 1920 1080 "screenshots/30-analysis-$key.png" "$BASE/#/analysis$q"
  shot 1920 2300 "screenshots/30-analysis-$key-full.png" "$BASE/#/analysis$q"
done

#!/bin/bash
# 无头 Chrome 1440×900 截图：09–17 国际对标模块
cd "$(dirname "$0")/.."
OUT=screenshots/1440
i=9
for r in evidence interview colreg whatif hf systemic recs knowledge access; do
  n=$(printf "%02d" $i)
  google-chrome --headless=new --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --window-size=1440,900 --virtual-time-budget=2500 \
    --screenshot="$OUT/${n}-${r}-1440.png" "file://$PWD/prototype/index.html#${r}" >/dev/null 2>&1
  echo "$OUT/${n}-${r}-1440.png"
  i=$((i+1))
done

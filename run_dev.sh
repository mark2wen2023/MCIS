#!/usr/bin/env bash
# 本地开发：③ Python 调查服务（127.0.0.1:8765）+ ④ Web 工作台（127.0.0.1:5173 dev / 4173 preview）。
# 用法：./run_dev.sh            后端 + Vite dev server（热更新）
#       ./run_dev.sh --preview  后端 + 先 npm run build 再 vite preview
# 环境变量：MCIS_DATA_DIR（默认 service/data，首次启动自动写入虚构 Lily/Mary 演示案）、MCIS_PORT（默认 8765）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:-dev}"
export MCIS_PORT="${MCIS_PORT:-8765}"
export MCIS_API="http://127.0.0.1:${MCIS_PORT}"

if [[ ! -x "$ROOT/service/.venv/bin/python" ]]; then
  echo "[run_dev] 创建 service/.venv ..."
  python3 -m venv "$ROOT/service/.venv"
  "$ROOT/service/.venv/bin/pip" install -q -r "$ROOT/service/requirements.txt"
fi
if [[ ! -d "$ROOT/web/node_modules" ]]; then
  echo "[run_dev] npm install ..."
  (cd "$ROOT/web" && npm install --no-audit --no-fund)
fi

pids=()
cleanup() { for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done; wait 2>/dev/null || true; }
trap cleanup EXIT INT TERM

echo "[run_dev] 后端 → http://127.0.0.1:${MCIS_PORT}  (数据目录 ${MCIS_DATA_DIR:-service/data})"
(cd "$ROOT/service" && exec .venv/bin/python -m mcis_service) &
pids+=($!)

for _ in $(seq 1 60); do
  curl -sf "http://127.0.0.1:${MCIS_PORT}/api/v1/cases" >/dev/null 2>&1 && break
  sleep 0.5
done
curl -sf "http://127.0.0.1:${MCIS_PORT}/api/v1/cases" >/dev/null || { echo "[run_dev] 后端启动失败" >&2; exit 1; }

cd "$ROOT/web"
if [[ "$MODE" == "--preview" ]]; then
  npm run build
  echo "[run_dev] 前端 → http://127.0.0.1:4173/#/evidence"
  npx vite preview --host 127.0.0.1 --port 4173 --strictPort &
else
  echo "[run_dev] 前端 → http://127.0.0.1:5173/#/evidence"
  npx vite --host 127.0.0.1 --port 5173 --strictPort &
fi
pids+=($!)
wait -n "${pids[@]}"

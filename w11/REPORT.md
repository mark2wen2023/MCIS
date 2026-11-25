W11 单边原文：真浏览器通过（固定验收 b40a6ca 官方脚本 verify-only 与 --browser 均为退出码 0，未改工装、未改产品）

# MCIS W11 单边原文显式读取真浏览器验收

- 执行时间：2026-11-25 23:58 至 2026-11-26 00:00（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 固定验收：`b40a6cacf91ba0d8b297377d31162e404e468e8d`（2026-11-25 22:57:42 +0800，“test(w11): assert ECFC excerpt requests occur only on explicit reads”）。相对 `41eb599f5a42eb2d0938ad4212936a0949a1cef5` 仅多 `tests_acceptance/w11-edge-host-optin/browser_check.py` 中 8 行浏览器断言。本轮按该提交原脚本跑通，未再改验收文件，也未改产品。
- 独立工作树 `/workspace/mcis-w11-b40a6ca`。隔离试点，不是生产入口。
- Chrome：Google Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`）。官方脚本以 `chromium_sandbox=True` 启动，没有 `--no-sandbox`。现成 Python Playwright 1.65.2（支持 `route_web_socket`），未新装依赖。
- 服务只监听 127.0.0.1；每轮临时 SQLite；页面流量限制在该回环源，拒绝 WebSocket 与 Service Worker。仅合成案与本地真实服务。不接真实模型或真实数据。未跑、也未把 HTTP-only / Happy DOM 写成真浏览器通过。
- 未改产品，未发 CI，未合并，未部署。

## 1. 固定核对（verify-only）

用现成本地 Git 对象，不 fetch：

```sh
<existing service python> -I -B tests_acceptance/w11-edge-host-optin/pinned.py \
  --repository /workspace/maritime-sim-design --verify-only
```

退出码 **0**。打印 `W11 pins: 186 service/original + 3 UI; no fetch`。186 个固定服务/原文源与 3 个 ECFC UI blob（`EdgeSelection.tsx` / `Graph.tsx` / `model.ts`，来自 `d9187fe`）全部命中既有对象。日志：`logs/01-verify-only.*`。

## 2. 真浏览器（--browser）

同一 pinned 入口，加上现成 Chrome / Python Playwright 与空输出目录：

```sh
MCIS_NODE_MODULES=<existing web/node_modules> \
MCIS_HOST_PYTHON=<existing service .venv/bin/python> \
MCIS_BROWSER_BIN=/opt/google/chrome/google-chrome \
MCIS_BROWSER_PYTHON=<existing python-with-playwright> \
MCIS_W11_BROWSER_OUT=<empty abs dir> \
<existing service python> -I -B tests_acceptance/w11-edge-host-optin/pinned.py \
  --repository /workspace/maritime-sim-design --browser
```

退出码 **0**（`browser-out/exit-code.txt` 亦为 0）。打印：

- `Browser: Google Chrome 156.0.8078.47 ; chromium_sandbox=True`
- `revised: excerpt POST checkpoints 0/1/2; no automatic read`
- `revoke: excerpt POST checkpoints 0/1/2; no automatic read`
- `W11 actual sandboxed Chromium + loopback service: reread after revision/revocation PASS`

改版与撤销为两轮独立合成案。每轮：选边（E01）0 次原文请求；确认点击「查看该连线关联出处」后 1 次且 200；改版/撤销后再点被拒（404）累计 2 次。每轮 custody 恰好 1 次 Register 和 1 次 Access，`commands=[]`（零回放跳转），哈希链有效。T+109 原文时刻为 `2026-02-01T12:01:49.000Z`（成功读取可见「原始记录 UTC（非事件时刻）」；拒绝后该时刻消失，并显示「出处不可用；未显示旧内容。」）。无跨源请求。

日志：`logs/02-browser.*`、`logs/02-browser-run.log`。

## 3. 截图

官方脚本写出的四张真页面截图（改版/撤销各一次成功读取与一次拒绝；两轮起始状态相同，故两张读取图互为同一内容，两张拒绝图亦同）：

- `screenshots/revised-read.png`：改版轮，确认读取后可见 T+109 `2026-02-01T12:01:49.000Z`
- `screenshots/revised-denied.png`：改版后再次点击，出处不可用、未显示旧内容
- `screenshots/revoke-read.png`：撤销轮成功读取，同样 T+109
- `screenshots/revoke-denied.png`：撤销后再次点击被拒

## 4. 未验

Firefox / WebKit；headed；生产路由或生产入口；真实模型或真实案卷；远程 CI。Happy DOM / 非浏览器预检与 HTTP-only 未当作真浏览器通过。

## 5. 文件

`logs/00-env.txt`、核对与浏览器原始日志；`screenshots/`；`browser-out/`（官方 `run.log`、`exit-code.txt` 与四张 PNG）。

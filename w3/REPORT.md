W3 草稿冲突：真浏览器通过（固定验收 6a231db 官方脚本 --build-only 与浏览器运行均为退出码 0；192 针与产品底版 bd02094 一致；未改工装、未改产品）

# MCIS W3 确定冲突保留未交草稿真浏览器验收

- 执行时间：2026-11-26 01:28–01:29（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 固定验收：`6a231db3ad4821e450af869def15f39ba95803ea`（2026-11-25 23:21:51 +0800，“test(w3): add sandboxed browser gate for protected draft recovery”）。相对产品底版仅新增 `tests_acceptance/w3-conflict-chromium/{README.md,page.tsx,pins.json,run.cjs}`。本轮按该提交原脚本跑通，未再改验收文件，也未改产品。
- 产品底版：`bd02094a7cbb95d9ebb24a33e51bab2e695cccd7`（2026-11-25 20:12:53 +0800，“Recover unsaved trial issue drafts after a definite revision conflict”）。
- 独立工作树 `/workspace/mcis-w3-6a231db` 作为固定源码根。`pins.json` 中 192 个固定源与工作树文件、以及底版 `bd02094` 的 Git blob 逐一对照，全部一致。
- Chrome：Google Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`）。官方脚本以 `chromiumSandbox:true` 启动，没有 `--no-sandbox`。现成 Node Playwright 1.63.0-alpha-2026-08-31，未新装依赖。
- 静态页与试验宿主仅监听 127.0.0.1；临时 SQLite。页面请求限制在本源 `/` 与 `/app.js`。仅合成案 `CASE-TRIAL-FICTIONAL`。不接真实模型或真实数据。未把 HTTP-only 或 Happy DOM / DOM 模拟写成真浏览器通过。
- 未改产品，未合并，未部署，未触发远程 CI。

## 1. 固定核对与打包

```sh
MCIS_SOURCE_ROOT=<worktree 6a231db> \
MCIS_NODE_MODULES=<existing web/node_modules> \
node tests_acceptance/w3-conflict-chromium/run.cjs --build-only
```

退出码 **0**。打印 `{"stage":"bundle","base":"bd02094a7cbb95d9ebb24a33e51bab2e695cccd7","pins":192,"bytes":1281976}`。日志：`logs/01-build-only.*`。

## 2. 真浏览器

同一入口，加上现成 Chrome、Node Playwright、现成服务 Python，以及尚不存在的证据目录：

```sh
MCIS_HOST_PYTHON=<existing service .venv/bin/python> \
MCIS_PLAYWRIGHT=<existing playwright package> \
MCIS_CHROMIUM=/opt/google/chrome/google-chrome \
MCIS_BROWSER_EVIDENCE_DIR=<absent abs dir> \
node tests_acceptance/w3-conflict-chromium/run.cjs
```

退出码 **0**。`exit.json`：`pass: true`，`version: Google Chrome 156.0.8078.47`，`chromiumSandbox: true`，阶段 `launch` → `card-a-conflict` → `card-b-no-rebind` → `store-reopen` → `complete`，`cleanupErrors: []`。无跨源请求，无页面错误。

1440 宽：合成卡甲在真实版本冲突（409 / `ISSUE_HOST_REJECTED`）后保留未交草稿「合成保留稿甲：仍针对原判断」，须重读并重选当前来源 EV-001 后方可写入（expectedRevision 2，against 1）。卡乙在判断从 #1 变为 #2 后，草稿「合成保留稿乙：不重新绑定」仍在但禁止提交，提示「原草稿针对判断 #1；当前判断 #2」，变更判断不能直接复用。重开同一临时 SQLite 后，390 窗口分别读回：卡甲版本 3 且历史含「合成保留稿甲」与 EV-001；卡乙版本 2 且含「并行添加新的判断」，不含甲/乙未交草稿。两张卡相互独立。

脱敏回执见 `logs/02-browser-exit.json`（官方 `exit.json`，仅作用域内 action/caseId/issueId/revision/code/status）。日志：`logs/02-browser.*`。

## 3. 截图

官方脚本写出的四张合成页截图：

- `screenshots/01-definite-conflict.png`：1440，确定冲突，未交草稿甲仍保留且不可直接提交
- `screenshots/02-no-rebind.png`：1440，判断已变，禁止把原草稿直接绑到新判断
- `screenshots/03-card-a-reopened.png`：390，重开后卡甲版本 3，稿甲已入历史
- `screenshots/04-card-b-reopened.png`：390，重开后卡乙版本 2，与卡甲独立

## 4. 未验

Firefox / WebKit；headed；完整响应式签收；生产登录或挂载；真实模型或真实案卷；远程 CI。Happy DOM 不确定/错配响应路径未在本轮作为真浏览器结果。

## 5. 文件

`logs/00-env.txt`、打包与浏览器原始日志、脱敏 `exit.json`；`screenshots/`；`browser-out/`（官方 PNG 与 `exit.json`）。

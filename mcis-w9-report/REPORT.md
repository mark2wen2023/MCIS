W9 环境记录恢复：真浏览器通过（固定验收 3d0e46e 官方脚本 --build-only 与浏览器运行均为退出码 0；73 针与产品底版 26dd466 一致；未改工装、未改产品）。HTTP-only 未跑，不算浏览器。

# MCIS W9.2 环境保存恢复真浏览器验收

- 执行时间：2026-11-26 03:45–03:47（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 固定验收：`3d0e46ef82ac2c7bcbf85741ba315e3cf1cea848`（2026-11-26 01:36:41 +0800，“test(W9): add pinned Chromium gate for environment save recovery”）。相对产品底版仅新增 `tests_acceptance/w92-chromium/{README.md,entry.tsx,host.py,pins.json,run.py}`。本轮按该提交原脚本跑通，未再改验收文件，也未改产品。
- 产品底版：`26dd466fcbdeb8422fcb54a5985d93df2103f4cc`（2026-11-25 20:03:46 +0800）。73 个固定 Git blob 与工作树及底版逐一对照，全部一致。
- Chrome：Google Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`）。官方脚本以 `chromium_sandbox=True` 启动，没有 `--no-sandbox`。现成 Python Playwright 1.65.2（支持 `route_web_socket` 与 `Route.fetch(max_retries=...)`），CPython 3.13.5。现成服务 Python 与 `web/node_modules`（package-lock SHA 与既有树一致）。未新装依赖。
- 试验宿主仅 127.0.0.1 + 临时 SQLite。仅合成案。页面请求限制在该回环源，拒绝 WebSocket 与 Service Worker。未跑 `--http-only`，也不把它写成真浏览器通过。本项是隔离合成环境页，不是完整产品壳或生产签收。
- 未改产品，未合并，未部署，未触发远程 CI，未安装任何软件。

## 1. 固定核对与构建

退出码 **0**。打印 `W9.2 pinned 73 exact product blobs at 26dd466…`，`W9.2 exact EnvironmentPage shell built: JS 801865 bytes`。日志：`logs/01-build-only.*`。

## 2. 真浏览器

退出码 **0**。`receipt.json`：`result=passed`，`trueBrowser=true`，`browserVersion=Google Chrome 156.0.8078.47`，`chromiumSandbox=true`，`mode=chrome`，`browserFixturePostCount=1`，`observationRows=1`，`observationWriteAuditRows=1`，`auditChainValid=true`。读回 SHA-256 `a177b1ec8d0ec2e1c6843346f549dbaec1383501a64875ff4df7796e7215e2d4`。官方打印：`W9.2 normal sandbox Chrome source, loopback response loss, read-only reconciliation, SQLite reopen PASS`。

流程（1440 后 390，互不替代 HTTP-only）：

- 第一次保存：工装把唯一 POST 转发到真实服务，等待 201 后丢弃成功响应的投递；界面显示「保存结果尚未确认…请先只读核查，不要重复提交。」此时列表仍为空，保存按钮已撤下。
- 显式「核查保存结果（只读）」后找回同一记录 SYN-W9-01，不再发第二次 POST。
- 同一临时 SQLite 重启后，390×844 新会话按原字节读回；观测时刻为「未知」，流速 0 kn，来源「合成来源第 7 页」等保留。另一合成案 `synthetic-env-unrelated` 为空。库中仅一行观测、一条 `environment.observation.create` 审计，链有效。

日志：`logs/02-browser.*`、`logs/02-browser-receipt.json`。

## 3. 截图

- `screenshots/01-uncertain-desktop.png`：丢响应后不确定提示与只读核查按钮
- `screenshots/02-confirmed-desktop.png`：只读恢复后同一条已保存记录
- `screenshots/03-reopened-narrow.png`：390 重启后按原字节读回
- `screenshots/04-separate-case-narrow.png`：另一合成案为空

## 4. 未验

Firefox / WebKit；headed；完整产品壳；动力学回放；真实案卷或正式身份；远程 CI。`--http-only` 未跑，也不算真浏览器。

## 5. 文件

`logs/00-env.txt`、针核对、构建与浏览器原始日志、`receipt.json`、`screenshots/`、`browser-out/`。

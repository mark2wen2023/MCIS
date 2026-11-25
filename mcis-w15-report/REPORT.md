W15 引擎不可用负向页：阻塞（固定验收 9ca1c12 官方 `--build-only` 退出码 0，339 针与产品底版 2c72d02 一致；官方 `--browser` 两次在构建后于真实 Chrome 会话中挂起，无官方截图、无 receipt，未改工装绕过）。此为负向关口，不是真 .NET 或成功出图。HTTP-only 未跑，不算浏览器。

# MCIS W15 引擎不可用时的页面（负向；阻塞）

- 执行时间：2026-11-26 04:49–05:01（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 固定验收：`9ca1c12d04db524e385f2509a4e2cae5cb44605c`（2026-11-26 01:36:45 +0800，“test(W15): add sandboxed browser gate for unavailable analysis core”）。相对产品底版仅新增 `tests_acceptance/w15-source-chromium/{README.md,host.py,pins.json,run.py}`。本轮按该提交**原脚本**执行，**未改验收文件、未改产品**。未并跑后续正向核心候选。
- 产品底版：`2c72d022f3d3275af637b0cdc6e545735e3200a9`（2026-11-24 09:22:48 +0800）。339 个固定 Git blob（33 contracts + 146 service + 2 tools + 158 web）与工作树及底版逐一对照，全部一致。
- Chrome：Google Chrome 156.0.8078.47。官方脚本 `chromium_sandbox=True`，没有 `--no-sandbox`。现成 Python Playwright 1.65.2，CPython 3.13.5。现成服务 Python 与 `web/node_modules`。未新装依赖。
- 试验宿主仅 127.0.0.1；`MCIS_DOTNET` 指向故意不存在的本地路径。仅合成案。未跑 `--http-only`。
- 未改产品，未合并，未部署，未触发远程 CI，未安装，未减断言。

## 1. 固定核对与构建

退出码 **0**。打印 `W15 pinned 339 exact Git blobs at 2c72d02…`，`Built exact product entry: 4601289 JS bytes`。日志：`logs/01-build-only.*`。

## 2. 官方真浏览器（两次，均挂起）

同一命令：官方 `run.py --browser /opt/google/chrome/google-chrome`，正常沙箱。两次均在针与构建打印之后停止输出：无三张官方 PNG、无 `receipt.json`、无 stderr 断言失败信息。宿主已在 127.0.0.1 健康，合成案准备数据已写入 SQLite；对同一库执行官方同款 `dump()` 可立即完成，故挂起点在随后的 `app_ui` / `page.goto(origin+"/#/systemic?case=…")`（官方默认 `wait_until="load"`）。Playwright 默认 30 秒导航超时在两次挂起中均未触发。

- 第一次：约 4 分钟后，为取栈误发 SIGUSR1，run.py 退出码 **138**（128+10）。见 `attempt1/`。
- 第二次（未改脚本重跑）：再次超过 3 分钟同样挂起后，以 SIGTERM 结束，退出码 **143**（128+15）。见 `attempt2/`。不算通过。

官方打印的 PASS 字符串未出现。503 / 不以样例图替代 / 切案清空 / 390 只读重启等业务断言**未验**。

## 3. 非正式诊断（不算真浏览器通过）

为定位挂起，另用相同 Chrome/沙箱/宿主，将 `page.goto` 设为 `wait_until="domcontentloaded"`、超时 20 秒。约 4 秒内标题与「系统性分析 · Bow-tie 假设草拟」可见，合成来源 EV-001 已出现。该诊断**不是**官方脚本退出码，也**不**代替 503 负向界面断言。材料在 `diag/`，截图 `diag/shots/diag-after-goto.png`。本轮按派遣未改官方工装、未把该诊断写成通过。

## 4. 未验

官方真浏览器负向流程（明确 503、无样例图、无端点跳转、切案清空、SQLite 重启后 390 只读且库不变）；HTTP-only；Firefox / WebKit；headed；真 .NET 或成功出图；正向核心候选（按派遣不并跑）；正式身份、真实案卷、远程 CI。

## 5. 文件

`logs/00-env.txt`、针核对、构建日志、两次官方浏览器原始日志；`attempt1/`、`attempt2/`；`diag/`（非正式）。

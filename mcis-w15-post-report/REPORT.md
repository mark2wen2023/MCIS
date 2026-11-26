# MCIS W15 同一 POST 双侧取证（有界诊断）

- 执行时间：2026-11-26 08:19–08:22（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 诊断提交：`06de2510cfacdc938aeb05e7ef2bc85d6a5d68ce`（2026-11-26 07:14:06 +0800，“test(w15): correlate browser and ASGI completion of the same preview”）。按 `tests_acceptance/w15-source-chromium/DIAGNOSIS.md` **原 diagnose.py** 跑一次。只把运行器换成该脚本，其余参数按 README；新的未用过证据目录；外层 `timeout --signal=TERM --kill-after=10s 150s`。未手发信号，未关沙箱，未改产品或工装，未减断言，未补发第二笔预览 POST。
- 本诊断不覆盖此前阻塞回执（含 9ca1c12 官方两次挂起、3d711f4 取栈停在 `app_ui:162` `Response.json()`），不算整体验收。
- 产品底版：`2c72d022f3d3275af637b0cdc6e545735e3200a9`。官方打印「W15 pinned 339 exact Git blobs」并完成正式页面构建（JS 4,601,289 字节）。
- `run.py` SHA-256：`3d379e2595992eb0b55a7e32ad1c9848424d555ac082c7d0e89b7c948fc3b721`，与 diagnose 针比对一致。
- Chrome：Google Chrome **156.0.8078.47**。官方脚本 `chromium_sandbox=True`，没有 `--no-sandbox`。现成 Python Playwright 1.65.2。宿主仅 127.0.0.1。仅合成案。未安装，未走外网。

## 1. 退出码

| 步骤 | 退出码 |
| --- | --- |
| 有界诊断（`timeout` 150s + `diagnose.py` 跑本提交 `run.py`） | **1**（官方进程自行结束，未用到外层 150s TERM） |

`receipt.json`：`passed=false`，`browserVerified=false`，`browserVersion=Google Chrome 156.0.8078.47`。无三张原截图。无官方 PASS 字符串。host-first.log 为 0 字节。未创建 host-reopened.log。

## 2. 双侧对照（同一预览 POST，未补发第二笔）

**浏览器：** 点击「运行结构核查（不保存）」在 +6.526s（`app_ui:168`）。随即 `page.on("request")` 进入 `net()`（说明浏览器已发出该预览 POST 的 request 事件），但 `net()` 写 `sys.stderr` 时抛出 `NameError: name 'sys' is not defined`。本提交的 `run.py` **没有** `import sys`。stderr 中 **0** 条 `W15 BROWSER` 行。两次事件监听错误都来自 `request` 回调；未见 `response` / `requestfinished` / `requestfailed` 进入 `net()`（若进入同样会 NameError）。随后 `page.expect_response` 在 30000ms 超时（`TimeoutError`，TRACE `app_ui:167 exception` 于 +36.535s）。

**宿主：** `host-first.log` 为空；stderr 中也无 `W15 HOST`。未记录 `preview request`、`sent_headers status=503`、或 `sent_final bytes=… sha256=…`。因此没有可对照的 503/final 字节与指纹。POST 是否到达 ASGI 为 **未验**。

**对照结论：** 无法比较宿主最终字节/指纹与浏览器收包。浏览器未记录 `requestfinished` 或 `requestfailed`。未改工装、未补发第二笔。

## 3. 未验

原 gate 完整通过；JSON 正文读取（本次在 `expect_response` 处已失败，未到达先前的 `result.json()` 停点）；宿主 final send；alert / 切案 / 390 重启；HTTP-only；Firefox / WebKit；headed；真 .NET。未改产品，未合并，未部署，未触发远程 CI。

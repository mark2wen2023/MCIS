# MCIS W15 原浏览器卡点取栈（有界诊断）

- 执行时间：2026-11-26 06:42–06:46（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 诊断提交：`3d711f463e6a0224b6730cc96eecc2889e82db24`（2026-11-26 05:14:12 +0800，“test(w15): trace stalled browser gate without changing assertions”）。仅新增 `DIAGNOSIS.md` 与 `diagnose.py`。
- 原 runner：`9ca1c12d04db524e385f2509a4e2cae5cb44605c` 的 `tests_acceptance/w15-source-chromium/run.py`，SHA-256 `3ab818b4ac28480226aae596f9ac7f6b852cfd8c2c1a2e023af40170a560c7aa`，与 diagnose.py 针比对一致；`run.py` / `host.py` / `pins.json` / `README.md` 字节与 9ca1c12 相同。默认等待与全部业务断言未改。
- 产品底版：`2c72d022f3d3275af637b0cdc6e545735e3200a9`。官方脚本打印「W15 pinned 339 exact Git blobs」并完成正式页面构建（JS 4,601,289 字节）。
- Chrome：Google Chrome **156.0.8078.47**。官方脚本 `chromium_sandbox=True`，没有 `--no-sandbox`。现成 Python Playwright 1.65.2。宿主仅 127.0.0.1。仅合成案。未安装，未走外网，未改产品，未手发 SIGUSR1。先前的 `domcontentloaded` 诊断不算本次验收。

## 1. 有界诊断命令

按 `DIAGNOSIS.md`：把原 Chrome 命令的运行器路径换成 `diagnose.py`，其余参数不变；新的未用过证据目录；外层 `timeout --signal=TERM --kill-after=10s 150s`。45 秒栈由 `faulthandler.dump_traceback_later` 写到 stderr，无需向 Python 进程发信号。

只跑一次。

## 2. 退出码与产物

| 步骤 | 退出码 |
| --- | --- |
| 有界诊断（`timeout` 150s + `diagnose.py` 跑原 `run.py`） | **124**（GNU timeout：150 秒到点发 SIGTERM；不是断言通过） |

- stdout：针与构建成功。之后再无官方 PASS / receipt 打印。
- 证据目录只有空的 `host-first.log`。**没有** `receipt.json`，**没有**三张原截图（`01-core-unavailable-1440.png` / `02-case-switch-1440.png` / `03-restart-390.png`）。
- 原 gate **未**完整退出 0。按派遣，此结果不可报复核通过。

## 3. 最后阶段（TRACE）

最后一条 TRACE：`W15 TRACE +19.453s app_ui:162 line`。之后直到 45 秒栈与 150 秒 TERM，再无 TRACE。

关键路径（原 `run.py` 行号）：

- `show()` 已跑完：`page.goto`（第 139 行）约 0.935 秒完成，第 140 行标题可见，`show` 于 +19.169s 返回。先前「停在 page.goto」的怀疑**不成立**。
- 随后勾选合成来源、填写危险源/顶事件，`expect_response` + 点击「运行结构核查（不保存）」完成（第 158 行进入、第 159 行点击、第 158 行退出 with、第 160 行取出响应）。
- 第 161 行（`assert result.status==503 and result.header_value("cache-control")=="no-store"`）在 +19.452s 到达，并在 1ms 内执行完（因为出现了第 162 行的 line 事件）。
- 停点是第 162 行：`assert result.json()["code"]=="BOWTIE_CORE_UNAVAILABLE"`。卡在 `Response.json()`（或该断言求值）内部，未进入第 163 行，也未看到 exception/return。

因此：页面已打开，503 状态与 cache-control 断言已通过；业务上的正文 `code` 断言、alert 文案、切案清空、重启后 390 只读等均为 **未验**。无官方截图。

## 4. 45 秒脱敏栈

`faulthandler` 在诊断开始后 45 秒向 stderr 写出（完整原文见 `logs/45s-stack.txt`）。只看到一条 OS 线程，即 Playwright 同步 API 的事件循环，最内层停在 `selectors.select`：

```
Timeout (0:00:45)!
Thread 0x00007fd9e47c9780 (most recent call first):
  File "/usr/lib/python3.13/selectors.py", line 452 in select
  File "/usr/lib/python3.13/asyncio/base_events.py", line 2004 in _run_once
  File "/usr/lib/python3.13/asyncio/base_events.py", line 683 in run_forever
  File "/usr/lib/python3.13/asyncio/base_events.py", line 712 in run_until_complete
  File ".../playwright/sync_api/_context_manager.py", line 66 in greenlet_main
```

说明：`faulthandler` 只转储 OS 线程，不会单独列出 sync API 的 greenlet。`app_ui:162` 来自 TRACE，不在这份 OS 栈里。栈在 `greenlet_main` 结束，没有更多 Python 帧。未手发 SIGUSR1。

## 5. 未验

原 gate 完整通过（退出 0 + 三张原截图 + receipt）；HTTP-only；Firefox / WebKit；headed；真 .NET 或成功出图；正向核心（本项不是核心补验）。未改产品，未合并，未部署，未触发远程 CI，未关沙箱，未减断言。

# MCIS W15 同一 POST 双侧取证重跑（候选 3a2ef41）

- 执行时间：2026-11-26 09:43–09:47（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 修正候选：`3a2ef41e8280abb169e4bcc5a805d7fd49109af1`（2026-11-26 09:10:55 +0800，“test(w15): import sys for response trace callback”）。相对 `06de2510cfacdc938aeb05e7ef2bc85d6a5d68ce` 的 diff 仅为 `run.py` 增加 `import sys`，以及 `diagnose.py` 将 `ORIGINAL_SHA256` 更新为 `c6de8546d254651b028f80bdcd4fe0e5d87eb6411b019d86d73198f85bed4cde`。DIAGNOSIS.md / host.py / pins.json / README.md 无差异。已核对该针与本工作树 `run.py` 字节一致。未再改工装或产品。
- 按 `tests_acceptance/w15-source-chromium/DIAGNOSIS.md` **原 diagnose.py** 跑一次。新的未用过证据目录；外层 `timeout --signal=TERM --kill-after=10s 150s`。未手发信号，未关沙箱，未减断言，未补发第二笔预览 POST。
- 本诊断不覆盖此前阻塞回执，不算整体验收。
- 产品底版：`2c72d022f3d3275af637b0cdc6e545735e3200a9`。官方打印「W15 pinned 339 exact Git blobs」并完成正式页面构建（JS 4,601,289 字节）。
- Chrome：Google Chrome **156.0.8078.47**。官方脚本 `chromium_sandbox=True`，没有 `--no-sandbox`。现成 Python Playwright 1.65.2。仅 127.0.0.1。仅合成。未安装，未走外网。

## 1. 退出码

| 步骤 | 退出码 |
| --- | --- |
| 有界诊断（`timeout` 150s + `diagnose.py`） | **124**（GNU timeout：150 秒到点发 SIGTERM；不是断言通过） |

无 `receipt.json`，无三张原截图。`import sys` 修正在本次生效：无 `NameError`。

## 2. 同一 POST 双侧对照

只观察到一笔预览 POST。

**浏览器（stderr）：**
- `W15 BROWSER t=22547.378698 preview request status=-`
- `W15 BROWSER t=22547.450980 preview response status=503`
- **未见** `requestfinished` 或 `requestfailed`。

`page.expect_response` 已完成；第 171 行 `assert result.status==503 and cache-control==no-store` 已通过。最后 TRACE：`+5.144s app_ui:172 line`，即 `assert result.json()["code"]=="BOWTIE_CORE_UNAVAILABLE"`，随后直至 45 秒栈与 150 秒 TERM 再无 TRACE。与此前 3d711f4 取栈停点相同（仍为 `Response.json()`）。

**宿主（host-first.log）：**
- `preview request`
- `preview sent_headers status=503`
- `preview sent_final bytes=74 sha256=56d478d95ce7be6180ea5b0b14dc4b25d27eef1039fa14eba6e14a9e9a6780ff`

时序（同一 monotonic 时钟）：宿主 request 晚于浏览器 request 1.864ms；宿主在收到后 66.7ms 发出 503 头并几乎立即 `sent_final`（74 字节）；浏览器 `response 503` 出现在宿主 final 之后 3.680ms。

**对照：** 两端都看到这一笔 POST。宿主已完成 ASGI 终包（503，74 字节，上述指纹）。浏览器已收到 `response` 503 并通过状态/cache-control 断言，但未记录 `requestfinished`/`requestfailed`，且 `Response.json()` 卡住，故无法读取浏览器正文并与宿主指纹核对。按 DIAGNOSIS.md，仅有服务端 final send 不能证明浏览器已收全正文。

45 秒栈仍只见 Playwright 事件循环 OS 线程停在 `selectors.select` → `greenlet_main`。

## 3. 未验

原 gate 完整通过（退出 0 + 三张原截图 + receipt）；浏览器正文字节/指纹核对；alert / 切案 / 390 重启；HTTP-only；Firefox / WebKit；headed；真 .NET。未改产品，未合并，未部署，未触发远程 CI。

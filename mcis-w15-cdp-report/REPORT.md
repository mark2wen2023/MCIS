# MCIS W15 CDP Network 取证（候选 cc98de9）

- 执行时间：2026-11-26 10:19–10:22（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 独立候选：`cc98de9ac4888c684651a6eb9d397b0161164022`（2026-11-26 10:07:57 +0800，“test(w15): passively record Chrome network completion”）。相对 `3a2ef41e8280abb169e4bcc5a805d7fd49109af1` 仅新增 CDP Network 观察、DIAGNOSIS.md 说明，以及 `diagnose.py` 将 `ORIGINAL_SHA256` 更新为 `8d52dabc5db587479d02605472bb7a6cc1f46d55bbe7f3c5ddf585a3912352e6`（与本工作树 `run.py` 字节一致）。host.py / pins.json / README.md 无差异。未调用 `Network.getResponseBody` 或其他 CDP 正文读取。未再改工装或产品，未改原断言，未替换请求。
- 按 `tests_acceptance/w15-source-chromium/DIAGNOSIS.md` **原流程**跑一次。新的未用过证据目录；外层 `timeout --signal=TERM --kill-after=10s 150s`。未手发信号，未关沙箱，未补发第二笔预览 POST。
- 本诊断不覆盖此前阻塞回执，不算整体验收，不把诊断计作通过。
- 产品底版：`2c72d022f3d3275af637b0cdc6e545735e3200a9`。官方打印「W15 pinned 339 exact Git blobs」并完成正式页面构建（JS 4,601,289 字节）。
- Chrome：Google Chrome **156.0.8078.47**。官方脚本 `chromium_sandbox=True`，没有 `--no-sandbox`。现成 Python Playwright 1.65.2。仅 127.0.0.1。仅合成。未安装，未走外网。

## 1. 退出码

| 步骤 | 退出码 |
| --- | --- |
| 有界诊断（`timeout` 150s + `diagnose.py`） | **124**（GNU timeout：150 秒到点发 SIGTERM；不是断言通过） |

无 `receipt.json`，无三张原截图。原 gate **未**完整退出 0。

## 2. 同一 POST 三列对照

只观察到一笔预览 POST。

| 来源 | 事件 | 是否出现 | 细节 |
| --- | --- | --- | --- |
| CDP | requestWillBeSent | 是 | status=- encodedBytes=- |
| Playwright | request | 是 | status=- |
| 宿主 | preview request | 是 | — |
| 宿主 | sent_headers | 是 | status=503 |
| 宿主 | sent_final | 是 | bytes=74 sha256=56d478d95ce7be6180ea5b0b14dc4b25d27eef1039fa14eba6e14a9e9a6780ff |
| Playwright | response | 是 | status=503 |
| CDP | responseReceived | 是 | status=503 encodedBytes=- |
| CDP | loadingFinished | **否** | 缺失 |
| CDP | loadingFailed | **否** | 缺失 |
| Playwright | requestfinished | **否** | 缺失 |
| Playwright | requestfailed | **否** | 缺失 |

时序（同一 monotonic 时钟）：CDP requestWillBeSent → 0.38ms 后 Playwright request → 2.08ms 后宿主 request；约 66.6ms 后宿主发出 503 头并立即终包（74 字节，指纹与 3a2ef41 重跑相同）；2.745ms 后 Playwright `response 503`；再 0.828ms 后 CDP `responseReceived 503`。`encodedBytes` 在 responseReceived 上为 `-`（按 DIAGNOSIS.md，这是传输计数，通常出现在 loadingFinished，不是 JSON 正文长度）。

`expect_response` 与第 194 行 503/no-store 断言已通过。最后 TRACE：`+4.665s app_ui:195 line`，卡在 `assert result.json()["code"]=="BOWTIE_CORE_UNAVAILABLE"`。45 秒栈仍为 Playwright 事件循环停在 `selectors.select` / `greenlet_main`。即使 CDP 完成事件缺失，也未替换请求、未改原断言、未绕过沙箱、未读取 CDP 正文。

## 3. 未验

原 gate 完整通过；CDP/浏览器正文字节核对；alert / 切案 / 390 重启；HTTP-only；Firefox / WebKit；headed；真 .NET。未改产品，未合并，未部署，未触发远程 CI。

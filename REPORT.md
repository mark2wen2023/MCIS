# W4.1 迟到响应隔离验收报告（Grokbot）

时间：2026-11-26 19:08–19:09 Asia/Shanghai（CST, UTC+8）
派遣：#106 comment 7189129087
已接：#106 comment 7189909937（2026-11-26 18:50 Asia/Shanghai）

本项只补真实迟到响应子项，不重跑已通过的两视口 COG 预览 / 顺序切案 / 库重开基线。不是带锚校时、回写或 W4 整包。不把范围内通过报成整包通过。仅加隔离验收候选（验收脚本 / 合成测试宿主 ASGI 送出闸门），未改产品、未重建核心、未安装、未合并、未改 CI/main、未部署、未碰三维仓库或 /workspace/yuehai-*。未使用历史散落 DLL `7afd120c…`。未用 Playwright fulfill / 假正文。

## 验收候选与制品核对（未重建）

- 候选分支：`candidate/w41-late-response` @ `ed430db2aab3620be1c001194308691e7694bdd5`（2026-11-26 19:08:54 +0800，`test(W4): add isolated late-response preview gate`）。基于已通过定位修正 SHA `b1586b667402431763f4b984202107894ecd5884`，只新增 `tests_acceptance/w4-synthetic-late-response-browser/{README.md,run.py}`。
- 产品仍钉 `94d5e38c926fda232bb987b60fa9145e4bcf01a7`。
- 复用已验明出处的 `/workspace/mcis-w41-core-out`（mtime 2026-11-26 17:49:30 CST）。跑前跑后完整哈希均一致：
  - DLL：`f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf`
  - runtimeconfig：`3d25821758613e4cd940d143ccb03c93704140077e69104996832510f38f6598`
  - deps：`fda133109cf9fc926cbda09598ad344f75dc57ec02e345b6923ec5fe2dff9d12`

闸门设计（仅合成测试宿主）：真实核心算完 A 的 align-preview 后，宿主暂缓 `http.response.start` 与未改动正文；不拦 B；控制面 `GET /__w41-gate/status`、`POST /__w41-gate/release`。切 B 使用同文档 `location.hash`（避免 `page.goto` 触发文档级导航中止仍在途的 A 请求）。放行后用 Playwright `page.wait_for_timeout` 泵送请求完成事件（纯 `time.sleep` 不会投递 `requestfinished`）。

## 官方复跑结果

命令：`timeout --signal=TERM --kill-after=10s 150s run.py`（正常沙箱 Chrome 156.0.8078.47，`chromium_sandbox=True`，未用 `--no-sandbox`；`--core-dll` 为上列已核制品；服务仅 127.0.0.1）。未手发信号。退出码 **0**。无第一条失败。`receipt.json`：`passed=true`，`scope=synthetic late preview response only; not W4 whole package and not a baseline rerun`，`sandboxRequested=true`。

时间顺序（Asia/Shanghai, CST, UTC+8，同一秒内）：

| 事件 | 时间 | monotonic |
| --- | --- | --- |
| A 已被真实核心算出并闸住（held sha=`e8dd952a43315b9044d8fff637d1620fbbd640e0aa7b72faf83d8cea3745263c`，1556 字节，HTTP 200） | 2026-11-26 19:08:58.207 CST | — |
| B 浏览器请求完成（HTTP 200）；先看到 B 的 11° | 2026-11-26 19:08:58.688 CST | 34787.713273747 |
| 放行原 A 响应 | 2026-11-26 19:08:58.794570 CST | 34787.820 |
| 闸门送出原 A 正文（sent=true，sendError=null，sha 不变） | 2026-11-26 19:08:58.794780 CST | — |
| A 浏览器请求真实完成（requestfinished，failure=null，HTTP 200） | 2026-11-26 19:08:58.798103 CST | 34787.822852706 |

A 完成晚于 B 约 0.110s，且在放行后约 0.003s。`aCancelled=false`，`aNeverArrived=false`，`aFinishedAfterB=true`。浏览器读到的 A 正文 SHA-256 与闸门持有的真实核心响应一致：`e8dd952a43315b9044d8fff637d1620fbbd640e0aa7b72faf83d8cea3745263c`。不是仅 HTTP、不是 DOM 模拟。

B 前后：放行前截图可见案号 SYN-W41-X-B、来源 70/81、结果 11° 且「未入库 / 未全部校准」；放行后再次断言 B 的案号、11°、来源 70 与 81，不被 A 的 5°（45/50）覆盖。两张真尺寸截图均为 1440×900，像素 SHA-256 相同 `876301d817f4550662e419c8427d55bcb94e367305397571a8fed440472461a0`，说明 A 到达后画面仍为 B 的 11°。

SQLite 逻辑摘要（iterdump SHA-256）直接前、迟到序列后、真实服务重开后均为：`7d1bd0ef15e59177611d5e05704bd70dc9162ee24cb91db9a56a20afaaf389b4`。

已验：1440 视口真实迟到响应（合成 A/B、ASGI 送出闸门、真 Chrome 完成顺序、B 不被覆盖、库直接前后及重开后不变）。未验：390 视口迟到响应；已通过的两视口 COG 预览 / 顺序切案 / 库重开基线（本轮按派遣不重跑）；带锚校时、回写、W4 整包。

## 说明（验收候选调试，非产品失败）

正式通过跑之前，候选脚本曾出现过：Playwright `request.response()` 在闸门持有期间会阻塞，导致 150s 外超时（退出 124，未写出完整回执）；以及放行后若只用 `time.sleep` 不泵送 Playwright 事件循环，`requestfinished` 会延到 `context.close()` 才投递，被误判「不曾到达」。上述均只改隔离验收脚本，未改产品。本报告结论以退出码 0 的正式跑为准。

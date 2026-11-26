# W4.1 迟到响应 390×844 隔离验收报告（Grokbot）

时间：2026-11-26 19:47–19:48 Asia/Shanghai（CST, UTC+8）
派遣：#106 comment 7190559400
已接：#106 comment 7191146659（2026-11-26 19:46 Asia/Shanghai）

本项只补真实迟到响应的 390×844 视口，不重跑已通过的桌面（1440）迟到响应，也不重跑顺序切案基线。不是带锚校时、回写或 W4 整包。不把范围内通过报成整包通过。沿用同一隔离验收候选上的 `ed430db` 闸门机制，仅将实际浏览器视口改为 390×844 并保留全部原断言，另确认回执面板可读、无整页横向溢出。未改产品、未重建核心、未改超时门槛、未安装、未合并、未改 CI/main、未部署、未碰三维仓库或 /workspace/yuehai-*。未使用历史散落 DLL `7afd120c…`。未用 Playwright fulfill / 假正文。

## 验收候选与制品核对（未重建）

- 候选分支：`candidate/w41-late-response` @ `5723594b9789d951e25fd9d107fbb858fcfa52b7`（2026-11-26 19:47:41 +0800，`test(W4): run late-response gate at a requested viewport`）。基于已复核通过的 `ed430db2aab3620be1c001194308691e7694bdd5`，只改验收脚本：增加视口参数并在原断言之后检查回执面板可读性与整页横向溢出。超时门槛未改。
- 产品仍钉 `94d5e38c926fda232bb987b60fa9145e4bcf01a7`。
- 复用已验明出处的 `/workspace/mcis-w41-core-out`（mtime 2026-11-26 17:49:30 CST）。跑前跑后完整哈希均一致：
  - DLL：`f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf`
  - runtimeconfig：`3d25821758613e4cd940d143ccb03c93704140077e69104996832510f38f6598`
  - deps：`fda133109cf9fc926cbda09598ad344f75dc57ec02e345b6923ec5fe2dff9d12`

## 官方复跑结果

命令：`timeout --signal=TERM --kill-after=10s 150s run.py --viewport-width 390 --viewport-height 844`（正常沙箱 Chrome 156.0.8078.47，`chromium_sandbox=True`，未用 `--no-sandbox`；服务仅 127.0.0.1）。未手发信号。退出码 **0**。无第一条失败。`receipt.json`：`passed=true`，`viewport=390×844`，`scope=synthetic late preview response at the requested viewport only; not W4 whole package and not a desktop or baseline rerun`，`sandboxRequested=true`。

时间顺序（Asia/Shanghai, CST, UTC+8）：

| 事件 | 时间 | monotonic |
| --- | --- | --- |
| A 已被真实核心算出并闸住（held sha=`e8dd952a43315b9044d8fff637d1620fbbd640e0aa7b72faf83d8cea3745263c`，1556 字节，HTTP 200） | 2026-11-26 19:47:58.518 CST | — |
| B 浏览器请求完成（HTTP 200）；先看到 B 的 11° | 2026-11-26 19:47:58.979 CST | 35748.808628177 |
| 放行原 A 响应 | 2026-11-26 19:47:59.111027 CST | — |
| 闸门送出原 A 正文（sent=true，sendError=null，sha 不变） | 2026-11-26 19:47:59.111153 CST | — |
| A 浏览器请求真实完成（requestfinished，failure=null，HTTP 200） | 2026-11-26 19:47:59.113 CST | 35748.942634258 |

A 完成晚于 B 约 134.01 ms，且在放行后约 2.49 ms。`aCancelled=false`，`aNeverArrived=false`，`aFinishedAfterB=true`。浏览器读到的 A 正文 SHA-256 与闸门持有的真实核心响应一致：`e8dd952a43315b9044d8fff637d1620fbbd640e0aa7b72faf83d8cea3745263c`。不是仅 HTTP、不是 DOM 模拟。

B 前后：放行前与放行后均断言案号 SYN-W41-X-B、来源 70/81、结果 11° 且「未入库 / 未全部校准」，不被 A 的 5°（45/50）覆盖。两张视口截图均为 **390×844**：
- `w41-late-390-B-11deg-before-release.png`：91205 bytes，SHA-256 `99018721162708ce13337e17494784b64c8ae3f1b61660a83ba20fb1445198d5`，可见 B 的 11° 回执起始段；
- `w41-late-390-B-after-A-arrived.png`：106863 bytes，SHA-256 `67e06abaeb76e7e102330fc1479324642c805a827c5909ca3269f4f3d487c372`，仍为 SYN-W41-X-B / 11°。两图像素不同，是因为放行前的可读性检查把回执面板滚入视口，第二张拍到已滚动后的回执内容，不是 B 被 A 的 5° 覆盖。

回执面板（`临时预览结果`）在 390×844 可读：放行前后均可滚动入视、可见，盒宽 340、可见高度约 843.6，文本 982 字符，含案号与 11°。整页横向溢出：无。`documentElement.scrollWidth=390` 等于 `innerWidth=390`（放行前后一致）。文档可纵向滚动（scrollHeight=3888），不属于整页横向溢出。

SQLite 逻辑摘要（iterdump SHA-256）直接前、迟到序列后、真实服务重开后均为：`1cca655bc21e380ec61bad207f022463e574880ed68c9f44476b3878a2f0eb12`。

已验：390×844 视口真实迟到响应（合成 A/B、ASGI 送出闸门、真 Chrome 完成顺序、B 不被覆盖、回执面板可读、无整页横向溢出、库直接前后及重开后不变）。未验：桌面（1440）迟到响应与顺序切案基线（本轮按派遣不重跑）；带锚校时、回写、W4 整包。

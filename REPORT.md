# MCIS W15 切案来源读取诊断（候选 b46401a，基于 034bff8）

- 执行时间：2026-11-26 13:20–13:25（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 底版：`034bff8b1a72aba9c296e13615d637b90d1c3d47`。隔离候选：`candidate/w15-caseswitch-source-get-observe` @ `b46401aedd55f30504757338d040376e565aed03`。相对 034bff8 仅改验收/诊断文件：观察来源 GET 的状态与失败类别、切案后页面案号，以及原断言失败后用用户可见大厅入口作对照；更新诊断 SHA 针与 DIAGNOSIS.md。未改产品、未放宽断言、未添加重试、未补发预览 POST。
- `run.py` SHA-256 `04b972e3fd6ae1a361a03318bfe79f8ff9ab711bdf5e99bbc10881f12cf5013b`，与 diagnose 针一致。按原 DIAGNOSIS.md 参数加 `--workflow-only`（只为到达切案点，不再读 503 正文）。
- 外层 `timeout --signal=TERM --kill-after=10s 150s`。正常沙箱（`chromium_sandbox=True`，无 `--no-sandbox`）。真本机回环。只点一次合成预览 POST。
- Chrome：Google Chrome **156.0.8078.47**。现成 Python Playwright 1.65.2。未安装，未走外网。本项不是产品变化，不算验收通过。

## 1. 退出码与第一失败点

| 步骤 | 退出码 |
| --- | --- |
| 有界诊断（150s 外层 + `diagnose.py --workflow-only`） | **1**（官方进程自行结束，未用到 150s TERM） |

第一失败点（与上次相同，未重试、未放宽）：`show(CASE_B)` 的 `expect(panel).to_contain_text("Synthetic source beta")`（`#w153-draft-sources`）5 秒超时。`receipt.json`：`passed=false`，`browserVerified=false`。保留截图 `01-core-unavailable-1440.png`；02/03 未写出。

## 2. 分类（切到 B 后、原 hash 跳转窗口内的唯一来源 GET）

**已发后取消。** 关联唯一，不作未验。

- 切案后页面当前案号：可见「当前案件：SYN-W15-B」，hash 亦为 SYN-W15-B；`loadingStatus=1`，来源面板计数 0。
- 浏览器：发出 CASE_B 来源 GET，随即 `requestfailed`，失败类别 `net::ERR_ABORTED`，无 HTTP 状态。
- 宿主：该窗口内未收到 CASE_B 来源 GET（直至后续可见入口诊断才出现另一次）。
- 同一次切案过程中，预览 POST 亦出现 `requestfailed`（仍只一笔预览，不追 503 正文）。

## 3. 同案正向 HTTP 来源读取

- 对照：案 A 的 hash 首屏来源 GET 成功。浏览器 `response 200` + `requestfinished`；宿主 `sent_headers status=200`，`sent_final bytes=279`；页面来源面板出现。
- 案 B 同案正向读取：在原 hash 跳转上**未观察到**成功 GET。仅在其后的用户可见入口路径上观察到：浏览器 `response 200` + `requestfinished`；宿主 `sent_headers status=200`，`sent_final bytes=278`。

## 4. 用户可见入口 vs 现有 hash 跳转

行为**不同**。原 `page.goto` hash 跳转到 `/#/systemic?case=SYN-W15-B`：来源 GET 已发后取消，面板不出现。在原断言失败后，诊断仅通过页面操作「返回案件大厅」→「进入案件：SYN-W15-B」→ 导航「14 系统性分析」（不用直接 HTTP 取代 UI）：来源 GET 200 完成，宿主发出 278 字节，页面案号仍为 SYN-W15-B，来源面板出现。此对照不是重试，也不把原断言计作通过。

## 5. 未验 / 边界

未把本项记为工作流或整包通过。未改产品，未合并，未部署，未触发远程 CI。

# MCIS W15 工作流验页（候选 034bff8，--workflow-only）

- 执行时间：2026-11-26 12:41–12:43（北京时间，UTC+8）。Grok Bot 的 Linux 盒子。
- 固定候选：`034bff8b1a72aba9c296e13615d637b90d1c3d47`（2026-11-26 12:38:50 +0800，“test(w15): separate user workflow from response body inspection”）。`run.py` SHA-256 `c5f750fc1d17e1842196bfb36f4f751c58caf57b7e732e2a4f1150d9b340f5eb`，与 diagnose 针一致。按原 DIAGNOSIS.md 参数另加 `--workflow-only`。未再改工装或产品，未加日志，未重试。
- 外层 `timeout --signal=TERM --kill-after=10s 150s`。正常沙箱（`chromium_sandbox=True`，无 `--no-sandbox`）。真本机回环服务。只跑一笔合成预览 POST（测试脚本点击一次）。只隔离测试工具自己的 `result.json()`。
- 本项不替代整包，不是产品变化。
- Chrome：Google Chrome **156.0.8078.47**。现成 Python Playwright 1.65.2。未安装，未走外网。

## 1. 退出码

| 步骤 | 退出码 |
| --- | --- |
| 有界诊断（150s 外层超时 + `diagnose.py --workflow-only`） | **1**（官方进程自行结束，未用到 150s TERM） |

`receipt.json`：`passed=false`，`browserVerified=false`，`browserVersion=Google Chrome 156.0.8078.47`。未写出 `workflowVerified` / `bodyVerified`（未走到成功路径）。只保留到第一张原规格截图 `01-core-unavailable-1440.png`；`02-case-switch-1440.png` 与 `03-restart-390.png` 未写出。

## 2. 第一个失败的业务断言（未重试）

已通过（切案之前）：HTTP **503** 且 `cache-control=no-store`；请求所选证据 `sourceEvidenceIds=["EV-001"]`；页面 alert「计算核心暂不可用」且含「不会用示例结果代替真实计算」；`.w153-result` 计数为 0（无假图）；无「定位草稿端点」；已保存 `01-core-unavailable-1440.png`。宿主对该笔预览：`sent_headers status=503`，`sent_final bytes=74`。Playwright 先记录 `request` 与 `response status=503`。

随后 `show(CASE_B)` 在 `expect(panel).to_contain_text("Synthetic source beta")`（`locator("#w153-draft-sources")`）处失败：5 秒超时，element(s) not found。页面已有标题「系统性分析 · Bow-tie 假设草拟」，状态为「正在读取本案允许的登记来源…」。等待期间 stderr 另有一条预览 `requestfailed`（不是测试脚本第二次点击）。未再往后验两案隔离完成、390px 重启、SQLite 无额外写入。

## 3. 顺带 NetLog 数字（原私有文件仍在，未重跑、未打包原日志）

对已捕获的那一笔唯一预览 POST：

- `URL_REQUEST_JOB_FILTERED_BYTES_READ` 条数：**1**
- `byte_count` 总和：**74**
- 明确名为 EOF／完成／取消／错误的事件：**未观察到**

## 4. 未验

工作流成功路径（`workflowVerified=true`）；整包；390px 重启；SQLite 无额外写入；截图 02/03；把本项计作整包通过。未改产品，未合并，未部署，未触发远程 CI。

【Grokbot｜W17｜待复核】

**W17：服务失败（独立 API 验收 13/14，快照用例返回 500）；真浏览器通过**

### 范围
- 这个 SHA 上的 W17 只有 **W17.1 只读权限与脱敏工作台**，验收目录是 `tests_acceptance/W171/`，没有 `w17-*-live` 的 README，也没有 `DEFECTS/W17*`。
- W17 的编辑、认证、导出脱敏和全系统字段脱敏在这个 SHA 上都没有实现，记为未验。

### 版本
- 固定 SHA：`3ae5166b7522f63bf39827a02341c856e394a0c9`，用的是和 W4 同一个独立工作树，不是 main。
- 结束时 `git status --porcelain` 为空。
- `tests_acceptance/W171/verified-impl-sha256.txt` 冻结了 9 个文件，**其中 3 个哈希不一致**：access_workbench/router.py、AccessContent.tsx、caseContext.ts。三者都在 11-12 W17.1 验收之后被改过。router 在 e40ae83 里改成了 `BEGIN IMMEDIATE`。所以原 W17.1 验收结论不能直接沿用到 3ae5166。

### 工具
Python 3.13.5，pytest 9.2.0，Python Playwright 1.65.2，Node v24.22.1，Vite 8.3.8，Google Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`）。
浏览器沙箱正常（`chromium_sandbox=True`，没有用 `--no-sandbox`）。

### 命令与退出码
| 命令 | 退出码 |
|---|---|
| `cd service && PYTHONPATH=. .venv/bin/pytest -q ../tests_acceptance/W171/test_workbench.py` | 1（13 passed，1 failed） |
| 访问相关回归 6 个文件（test_access_workbench、test_interview_access_w52a、test_interviews_redaction、test_recommendation_content_access、test_report_bundle_attachment_access、test_reports_w162_access） | 1（236 passed，4 failed） |
| `cd web && bash tests/run-access-workbench-w171.sh` | 0 |
| 候选分支 `MCIS_BROWSER_BIN=/opt/google/chrome/google-chrome python tests_acceptance/W171/browser_real.py` | 0 |
| 仓库原版 browser_real.py | 未跑：写死了 `--no-sandbox`，违反沙箱规则 |

### 分项结果
**真实浏览器（真实 FastAPI + Vite + 有沙箱的 headless Chrome，127.0.0.1）**：通过。
- CASE-A 只读策略能正常显示，URL、顶栏、页面三处案号一致，也有「本地自报角色」提示。
- 没有回退到旧 `/access-policy` 接口；点「刷新」时清空旧数据。
- 旧案 A 的延迟响应在切到 B 之后才送达，没有把 A 的数据恢复出来。
- 旧身份的延迟响应在切到 Public 之后才送达，没有恢复数据，页面显示拒绝提示。
- 只有 GET 请求，没有页面错误。
- 说明：延迟是用 `route.fetch()` 拿到真实后端响应后推迟送达，没有伪造数据。

**HTTP 和服务端（真实 uvicorn，127.0.0.1，直接查 SQLite）**：部分失败。
- 通过：6 种角色 × 3 个案件的权限矩阵正确（调查组得 200 或 404，其他角色一律 403，响应一样，不泄露案件是否存在）；18 个响应都带 `no-store`；18 次 GET 前后 `audit_events` 都是 0 行。
- 通过：真跨线程并发。读取中途另一个线程写 v2，GET 仍返回 v1 加空事件，是单一快照；写方等了 1.04 秒后提交成功。
- **失败**：`test_policy_and_audit_are_one_snapshot` 返回 500。根因是 `sqlite3.OperationalError: database is locked`：测试在请求线程里同步再开一个连接去写，而端点已经用 `BEGIN IMMEDIATE` 占了写锁，这个写等满 busy timeout（约 5 秒）后失败，异常变成 500。快照不变量本身没被破坏，但仓库自带的验收用例在这个 SHA 上确实失败。是改测试（把写方放到另一个线程）还是改端点，请裁定；我没有改断言，也没有改产品。
- **失败（已知旧问题）**：`test_interviews_redaction.py` 的 4 项。完整笔录门禁返回 403，这些 11-11 的旧测试没有跟上新门禁。W17「按角色字段脱敏」这一项在这个 SHA 上没有能通过的测试。

**模拟 DOM 或 API 替身（不算验收）**
- node 的 model/render/transport 测试：通过。
- `web/tests/access-workbench-w171.browser.py` 的仓库外有沙箱副本：通过。它用的是真 Chrome，但 API 全部由替身返回。

### 首个错误与复现
```
cd service && PYTHONPATH=. .venv/bin/pytest -q ../tests_acceptance/W171/test_workbench.py
FAILED test_policy_and_audit_are_one_snapshot: 500 INTERNAL_ERROR（database is locked）
```

### 未验
- W17 的编辑、认证、导出脱敏和全系统字段脱敏（这个 SHA 上没有实现）。
- 仓库原版 browser 脚本原样运行（写死了 `--no-sandbox`）。
- 多视口和移动端，TypeScript 编译和 Vite 生产构建，Firefox 和 WebKit，有界面（headed）窗口。

### 测试工具改动
- 候选分支：https://github.com/mark2wen2023/MCIS/tree/candidate/w17-live-acceptance-grokbot（提交 `03ba941a973f14886815d57e53e00b874ec6ad29`，基于 3ae5166）
- 只改了 `tests_acceptance/W171/browser_real.py`（+7/−1）：去掉 `--no-sandbox`，改用 `chromium_sandbox=True`；另加可选截图 `W171_SHOTS`，断言没有改。

### 原件
- 证据目录（孤立分支，不会合并）：https://github.com/mark2wen2023/MCIS/tree/evidence/w17-grokbot-3ae5166/w17
- 报告：https://github.com/mark2wen2023/MCIS/blob/evidence/w17-grokbot-3ae5166/w17/REPORT.md
- 压缩包：https://github.com/mark2wen2023/MCIS/blob/evidence/w17-grokbot-3ae5166/w17/mcis-w17-report.tar.gz
- SHA-256：`fdb4f02c7a6848bebffddf3438673a9dc74d663fc4d7ecda1db34183e67fdbef`
- 截图：https://github.com/mark2wen2023/MCIS/tree/evidence/w17-grokbot-3ae5166/w17/screenshots

没有修改产品，没有触发 CI，没有合并，也没有部署。

@Dot 请在本帖回复 【Dot｜复核通过 / 需补证 / 待授权】。

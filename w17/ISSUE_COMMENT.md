【Grokbot｜W17｜待复核】独立复验 871db66

**W17@871db66：服务通过；真浏览器通过**

本回执是对固定提交 `871db66badc6566d82239ee701958c0ef8feb558` 的独立复验，不重跑旧回执。

### 版本
- 独立工作树检出 `871db66badc6566d82239ee701958c0ef8feb558`（2026-11-25 12:35 +0800，"Align evidence read policy across evidence views"）。运行前后 `git status --porcelain` 都为空。
- 相对 a80226d / 29cbfe2，产品只改了 `service/mcis_service/evidence/router.py`：custody 端点在读取后增加 `filter_evidence`，Restricted 证据对外部角色返回 403「受限证据」。

### 服务 / HTTP / SQLite（真实 uvicorn，127.0.0.1，合成 SYN-A / SYN-B）
通过，59/59。
- 调查组（LeadInvestigator、Investigator）可正常读取列表、单条、custody、intake。
- 受限角色被拒，**含 custody**：Public 四个端点均为 403。ExternalExpert、InterestedState、AgentService 的列表为 200 空数组（FR-05），单条、custody、intake 均为 403，响应中没有 Restricted 元数据。这是对先前 custody 泄漏的修复确认。
- 撤销 SYN-B 权限后，调查组对该案四个端点仍为 403；SYN-A 不受影响。
- 两案隔离：跨案摘要 404，列表不串案。
- 审计：种数据后 `audit_events=2`、`custody_events=2`（均为 Register）。调查组读取后、受限角色全部拒绝后、撤权后再读，两个计数都仍是 2，没有新增 Access 或 audit 行。

### 真实浏览器（同一 871db66 的服务 + Vite，正常沙箱 Chrome 156）
通过。
- 桌面 1440×900 和窄屏 390×844 工作流全部通过：未点选不读保管链；切案后迟到列表不回填；回执与登记一致；Public 和撤权后均拒绝并显示提示；全程只有 GET，结束后 SQLite 仍是 2 条 Register、2 条 audit。
- 仓库自带 EvidencePage 浏览器门禁（合成 API，无后端）：通过，12/12，`passed=true`，外部请求 0。
- W17.1 工作台真浏览器：仓库原版写死了 `--no-sandbox`，未原样运行；仓库外有沙箱副本通过。

### 模拟 DOM
未跑。仓库回执 `w17-evidence-selection-receipt` 仍锁定 29cbfe2 的源码哈希，在 `evidence/router.py` 处按预期失败（实际 `48e5dd41…`，锁定 `83dcd05e…`）。没有改固定校验。

### 单独列出（不计入上面的 W17 判定）
- SQLite 锁：W171 `test_policy_and_audit_are_one_snapshot` 仍失败（`database is locked` / 500）。
- 归档/导出：合成演示案 `GET /export` 仍返回 409 `ARCHIVE_RESTORE_UNSUPPORTED`。

### 原件
- 证据目录（孤立分支，不会合并）：https://github.com/mark2wen2023/MCIS/tree/evidence/w17-grokbot-871db66/w17
- 报告：https://github.com/mark2wen2023/MCIS/blob/evidence/w17-grokbot-871db66/w17/REPORT.md
- 压缩包：https://github.com/mark2wen2023/MCIS/blob/evidence/w17-grokbot-871db66/w17/mcis-w17-871db66-report.tar.gz
- SHA-256：`46ac678f99318d48882437cf58edcf9339013b526816177407d51517cca2d6ee`
- 截图：https://github.com/mark2wen2023/MCIS/tree/evidence/w17-grokbot-871db66/w17/screenshots

没有修改产品，没有触发 CI，没有合并，也没有部署。

@Dot 请在本帖回复 【Dot｜复核通过 / 需补证 / 待授权】。

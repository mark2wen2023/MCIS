W17@871db66：服务通过；真浏览器通过

# MCIS W17 独立复验 871db66

- 执行时间：2026-11-25 12:38–12:45（北京时间，UTC+8）。执行环境是 Grok Bot 的 Linux 盒子，uid 1000。
- 本回执是对 #106 的独立复验，不重跑 a80226d / 29cbfe2 / 3ae5166 的旧回执。
- 数据全部合成：虚构案件 SYN-A / SYN-B，两案都用 EV-001。服务和 Vite 只监听 127.0.0.1。
- 没改产品，没触发 CI，没合并，没部署，没碰三维仓库。没有候选分支（测试工具都放在仓库外）。

## 1. 版本

| 项 | 值 |
|---|---|
| 工作树 | `/workspace/mcis-w17-871db66`（独立 `git worktree add --detach`；先用令牌请求头 fetch，成功） |
| HEAD | `871db66badc6566d82239ee701958c0ef8feb558`（2026-11-25 12:35 +0800，"Align evidence read policy across evidence views"） |
| `git status --porcelain` | 运行前为空；运行中出现过未跟踪的 `.evidence-page-browser-dist/`，已删除；结束时为空 |
| 相对 29cbfe2 | 29cbfe2 是祖先。差异：验收目录 `tests_acceptance/w17-evidence-selection-receipt/`（a80226d 已加）+ **产品只改了** `service/mcis_service/evidence/router.py`（+3/−1） |
| 相对 a80226d | a80226d 是祖先。唯一产品差异就是上面那一处 router 改动 |
| custody 与 FR-05 | **已加上 Restricted 过滤。** `get_custody` 在 `require(..., "evidence_meta")` 之后增加：`item = service.load_item(...)`；`if not filter_evidence([item], ctx.role, get_policy(s, case_id)): raise problem(403, "FORBIDDEN", "受限证据")` |
| 验收目录 | `tests_acceptance/w17-evidence-selection-receipt/`（固定哈希仍指向 29cbfe2 的 blob，含旧版 router.py）；`web/tests/evidence-page-browser/`；`tests_acceptance/W171/`。没有 `DEFECTS/W17*` |

## 2. 工具

Python 3.13.5（service/.venv 按 requirements 新建）；Node v24.22.1（web 下 `npm ci`）；Google Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`）；Node 版 Playwright 1.63.0-alpha（W4 同一 pnpm 路径）；Python 版 Playwright 1.65.2（仓库外 venv）。沙箱：`chromiumSandbox/chromium_sandbox=True`，进程参数里没有 `--no-sandbox`，渲染进程 Seccomp=2、NoNewPrivs=1。详见 logs/00-env.txt。

## 3. 命令与退出码（工作树根目录）

| # | 命令 | 退出码 | 结果 |
|---|---|---|---|
| 1 | `node tests_acceptance/w17-evidence-selection-receipt/run.cjs --source <本工作树> --python <本工作树>/service/.venv/bin/python --web-modules <本工作树>/web/node_modules --happy-dom-entry <仓库外 happy-dom>/lib/index.js` | **1** | **预期的固定哈希不一致**：`pinned source mismatch: service/mcis_service/evidence/router.py`，实际 `48e5dd41…`，脚本仍锁定 29cbfe2 的 `83dcd05e…`。未改固定校验，套件未执行 |
| 2 | 真实 uvicorn `e2e_server.py --repo . --data /tmp/w17-871-data --port 18781` + `http_probe.py` | **0** | **59/59 通过** |
| 3 | 仓库浏览器门禁：vite build；predicates 13；request-policy 37；`check.py --chromium /opt/google/chrome/google-chrome --dist $PWD/.evidence-page-browser-dist --output <新目录>` | 0 / 0 / 0 / **0** | receipt：`passed=true`，`externalRequests=0`，12/12，Chrome 156 |
| 4 | 真实后端端到端 `run_e2e.sh 1440x900 vp1440` 与 `390x844 vp390`（uvicorn :18783 + Vite :18784，都来自 871db66 工作树） | **0 / 0** | 两种视口全部通过 |
| 5 | 仓库外副本 `tooling/w171_browser_sandboxed.py`（去掉 `--no-sandbox`，改用 `chromium_sandbox=True`；ROOT 指向本工作树） | **0** | `PASS real browser/API: …` |
| 6 | 仓库原版 `tests_acceptance/W171/browser_real.py` | 未跑 | 写死了 `--no-sandbox` |

## 4. 分项结果

### 4.1 HTTP 和 SQLite（真实 uvicorn，127.0.0.1:18781，create_app 全应用）：通过，59/59

种数据走真实 HTTP 的 `evidence-intakes:preview` / `:commit`。SQLite 用只读方式直接查询。角色覆盖 LeadInvestigator、Investigator、Public、ExternalExpert、InterestedState、AgentService。

| 项 | 结果 |
|---|---|
| 调查组可正常读取 | 通过。两名调查组成员对 SYN-A / SYN-B 的列表、单条、custody、intake 均为 200；列表各只有本案 EV-001（SOURCE-本案）；intake 的 requestDigest / sourceSha256 / fileName 与登记一致，不含 contentBase64 |
| 受限角色被拒（含 custody） | 通过。Public：四个端点（list / item / custody / intake）× 两案全部 **403**，响应里没有 Restricted 元数据。ExternalExpert、InterestedState、AgentService：列表 200 且为 `[]`（FR-05 Remove）；单条、**custody**、intake 均为 **403**，没有 `SOURCE-SYN-*`、文件名或 `Restricted`。这正是 a80226d 回执里 custody 泄漏的修复点，本 SHA 已生效 |
| 撤权后仍拒绝 | 通过。把 SYN-B 的 LeadInvestigator `evidence_meta` 改为 Deny 后，该案四个端点都是 403、无泄漏；SYN-A 的 intake 和 custody 仍为 200 |
| 两案隔离 | 通过。SYN-A 的登记摘要拿到 SYN-B 下查询 → 404，无 sourceSha256；EV-999 不返回本案元数据；SYN-A 列表不含 SOURCE-SYN-B |
| 读取或拒绝均不新增审计 | 通过，见下表 |

### 4.2 审计与保管链计数（SQLite 直查）

| 时点 | audit_events | custody_events |
|---|---|---|
| 种数据之后（两次 Register 各带 1 条登记审计） | **2** | **2**（SYN-A/EV-001 Register，SYN-B/EV-001 Register） |
| 调查组全部读取之后 | **2** | **2** |
| 四个受限角色全部拒绝之后 | **2** | **2** |
| 撤权后再读、全部结束 | **2** | **2**，仍只有 Register，没有 Access / Verify |

结论：本次所有 GET 读取和拒绝都没有新增 audit 行，也没有新增 custody 行。

### 4.3 真实浏览器 + 真实后端（871db66 的 uvicorn + Vite，正常沙箱 Chrome）：通过

自写驱动，没有 page.route，没有 fetch 替身。迟到响应由后端测试包装层在真实处理完成后推迟送出。1440×900 和 390×844 全部通过。

| 项 | 1440×900 | 390×844 |
|---|---|---|
| 进入 SYN-A：列表显示 SOURCE-SYN-A，保管链为「请选择证据」，不发 custody 请求 | 通过 | 通过 |
| 显式点选后 custody 200，出现「保管链 · EV-001」 | 通过 | 通过 |
| B→A→B 切案，前两次列表响应推迟后以 200 送达：当前 B 显示 SOURCE-SYN-B 和「请选择证据」，没有自动选中，也没有替 B 发 custody；迟到数据没有回填 SOURCE-SYN-A | 通过 | 通过 |
| 点选 B 并读取回执：SYN-B.txt、登记 SHA 和摘要一致，没有 SYN-A | 通过 | 通过 |
| 在 A 发起读回执后立刻切到 B：页面主动中止旧请求（net::ERR_ABORTED），没有回执、没有 SYN-A.txt | 通过 | 通过 |
| 切到 Public：列表 403，页面没有 SOURCE-SYN-B | 通过 | 通过 |
| 已选中 B 后撤销 LeadInvestigator 权限再读回执：403，显示 alert，没有回执 | 通过 | 通过 |
| 全程只有 GET；没有 download / :commit / :preview；没有外部请求；没有 pageerror | 通过 | 通过 |
| 结束后 SQLite：custody 2 行 Register，audit 2 行 | 通过 | 通过 |

说明：旧回执请求被页面中止，因此「迟到回执真正送到浏览器后再丢弃」这条路径仍未发生（未验）。迟到的**列表**响应确实送到了浏览器。

### 4.4 真实浏览器 + 合成 API（仓库门禁 evidence-page-browser，没有后端）：通过

fetch 由夹具控制。1440 / 390 宽度下 late=data/deny 与 conflicts=deny/empty/empty/data 共 12 项全部通过，外部请求 0。截图在 `receipt-evidence-page-browser/`。这不是端到端验收。

### 4.5 W17.1 工作台真浏览器（真实 FastAPI + Vite，都来自 871db66）：通过（仓库外有沙箱副本）

仓库原版写死 `--no-sandbox`，未原样运行。副本只改启动参数和截图路径，断言未改。覆盖：只读配置、不回退旧接口、刷新清空、旧案/旧身份迟到响应不恢复数据、Public 拒绝、无页面错误。

### 4.6 模拟 DOM

未跑。仓库回执脚本在核对 100 个固定 blob 时因 `evidence/router.py` 哈希不一致退出，后面的 Happy DOM 套件没有执行。这是预期行为，没有为了跑绿去改固定校验。

## 5. 未验

- 仓库原版 W171 `browser_real.py`（`--no-sandbox`）。
- 迟到回执真正送到浏览器后再丢弃。
- 外部角色在 UI 上点选 custody：列表为空，点不到行。本次泄漏修复已在 HTTP 层验证。
- 真实触屏、Firefox / WebKit、有界面窗口、原件下载与 Access 写入、生产认证。

## 6. 首个与 W17 本版本相关的「失败」（固定哈希脚本，预期）

```
cd /workspace/mcis-w17-871db66
node tests_acceptance/w17-evidence-selection-receipt/run.cjs \
  --source /workspace/mcis-w17-871db66 \
  --python /workspace/mcis-w17-871db66/service/.venv/bin/python \
  --web-modules /workspace/mcis-w17-871db66/web/node_modules \
  --happy-dom-entry /workspace/w17-tools/node_modules/happy-dom/lib/index.js
# 退出码 1
# AssertionError: pinned source mismatch: service/mcis_service/evidence/router.py
# actual   48e5dd4149076443062fdbe720d38ef58977b943
# expected 83dcd05ef1508b5d8f9d09ab46a9588da7f4b15f
```

真实 HTTP 与真浏览器验收本身没有失败。

## 7. 下列两项不计入上面的 W17 判定

见第 8 节单独列出。

## 8. 单独列出（不计入 W17 判定）

- **SQLite 锁：** `tests_acceptance/W171/test_workbench.py::test_policy_and_audit_are_one_snapshot` 仍失败，响应 500，根因仍是端点 `BEGIN IMMEDIATE` 与测试在请求线程里同步写库导致 `database is locked`。这是旧 W17.1 用例，与本次 custody FR-05 修复无关。日志：`logs/05-w171-snapshot.log`。
- **归档/导出：** `GET /export`（合成演示案、LeadInvestigator）仍返回 **409** `ARCHIVE_RESTORE_UNSUPPORTED`（「此案未通过完整恢复预检，未生成部分案件包」）。日志：`logs/05-export-probe.log`。

## 9. 文件

- `logs/`：00 环境、固定哈希；01 仓库回执（固定哈希失败）；02 真实 HTTP 探针；03 端到端两种视口；04 仓库浏览器门禁；05 单独列出的 snapshot / export；06 W171 沙箱副本。
- `screenshots/`：vp1440-*、vp390-*（真实后端端到端，各 7 张）；`w171/`（3 张）。
- `receipt-evidence-page-browser/`：仓库门禁 receipt.json 与截图。
- `tooling/`：全部在仓库外（e2e_server.py、http_probe.py、e2e_driver.cjs、run_e2e.sh、w171 沙箱副本、export 探针）。

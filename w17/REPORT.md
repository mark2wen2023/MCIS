W17：服务失败（独立 API 验收 13/14，快照用例返回 500）；真浏览器通过

# MCIS W17（W17.1 权限与脱敏只读工作台）验收报告

- 执行：2026-11-25 11:30–11:35（北京时间，UTC+8），Grok Bot Linux 盒子，uid 1000（非 root）。
- 数据：只用验收脚本生成的合成案件 CASE-A / CASE-B，放在临时目录；服务和 Vite 只监听 `127.0.0.1`。没用真实案卷或密钥，没部署、没合并、没触发 CI，也没碰三维仓库。

## 0. W17 在这个 SHA 上指什么
- ROADMAP 第 37 行：W17 是「权限矩阵 + 字段级脱敏 + 访问审计」（service + web）。这个 SHA 上**只实现了 W17.1 这一刀**：只读权限工作台（当前案的策略矩阵、字段规则声明、自报角色、最近 50 条策略变更审计）。ROADMAP 第 240–253 行明确写了「不是 W17 所有编辑/认证/导出功能已完成」。
- 验收目录是 `tests_acceptance/W171/`，包括 REPORT.md、test_workbench.py（独立 API）、browser_real.py（真实 FastAPI+Vite+Chromium）、server.py 和 verified-impl-sha256.txt。**没有 `w17-*-live` 那种 README**，复现命令写在 W171/REPORT.md 里。
- 没有 `DEFECTS/W17*`。相关的只有 `DEFECTS/W7ACCESS.md`。
- 缺失项：W17 的策略编辑、真实认证、字段脱敏在全系统的落实、导出脱敏，这个 SHA 上都没有，也就无从验收（未验）。

## 1. 版本
| 项 | 值 |
|---|---|
| 工作树 | `/workspace/mcis-w4-3ae5166`（和 W4 同一个） |
| HEAD | `3ae5166b7522f63bf39827a02341c856e394a0c9`；结束时已切回 detached 3ae5166，`git status --porcelain` 为空 |
| 冻结哈希 `tests_acceptance/W171/verified-impl-sha256.txt` | **9 个里 3 个不一致**：`service/mcis_service/access_workbench/router.py`、`web/src/accessWorkbench/AccessContent.tsx`、`web/src/caseContext.ts`。三者都是 W17.1 验收（935410a，11-12 14:31）之后被别的包改过：router 在 e40ae83（11-12 18:50）把显式 `BEGIN` 换成了 `begin()`，也就是 **BEGIN IMMEDIATE**，并加了 recommendation 事件保护；另外两个是 W5.2a / W14.4 / W15.3 / W18.3 / W20.3 的改动。完整 diff 见 logs/00-frozen-hash-drift.diff。**所以原 W17.1 验收结论不能直接沿用到 3ae5166** |

## 2. 工具
Python 3.13.5（service/.venv，pytest 9.2.0、FastAPI 0.165.0、SQLAlchemy 2.1.9、uvicorn 0.54.0）；Python Playwright 1.65.2（单独装在 `/workspace/w17-pyplaywright-venv`）；Node v24.22.1；Vite 8.3.8 / React 19.3.1（`web/` 下执行了 `npm ci`）；Google Chrome 156.0.8078.47（`/opt/google/chrome/google-chrome`）。

## 3. 命令与退出码
| # | 命令（工作目录） | 退出码 | 结果 |
|---|---|---|---|
| 1 | `cd service && PYTHONPATH=. .venv/bin/pytest -q -p no:cacheprovider ../tests_acceptance/W171/test_workbench.py` | **1** | 13 passed，**1 failed**：`test_policy_and_audit_are_one_snapshot` → 500 INTERNAL_ERROR |
| 1b | `cd service && PYTHONPATH=. .venv/bin/python -B <报告>/tooling/probe_snapshot.py`（诊断，复现同一竞态，但把异常打出来） | 0 | `CONCURRENT WRITER FAILED: OperationalError database is locked`，GET 返回 500 |
| 2 | `cd service && PYTHONPATH=.:.. .venv/bin/pytest -q -p no:cacheprovider tests/test_access_workbench.py tests/test_interview_access_w52a.py tests/test_interviews_redaction.py tests/test_recommendation_content_access.py tests/test_report_bundle_attachment_access.py tests/test_reports_w162_access.py` | 1 | 236 passed，4 failed（都在 test_interviews_redaction.py） |
| 2b | `<报告>/tooling/probe_interview_gate.py` | 0 | 三个笔录端点都返回 403「完整笔录内容不可访问」 |
| 3 | `cd web && bash tests/run-access-workbench-w171.sh` | 0 | `W17.1 model/render/transport tests passed` |
| 4 | 候选分支上：`W171_SHOTS=<报告>/screenshots MCIS_BROWSER_BIN=/opt/google/chrome/google-chrome /workspace/w17-pyplaywright-venv/bin/python -B tests_acceptance/W171/browser_real.py` | **0** | `PASS real browser/API: ...` |
| 5 | `<报告>/tooling/w171-ui-api-doubles.sandboxed.py`（web/tests/access-workbench-w171.browser.py 的仓库外副本，只去掉 --no-sandbox，并改了截图输出路径） | 0 | 通过（**API 替身 / 模拟**） |
| 6 | `cd service && PYTHONPATH=. .venv/bin/python -B <报告>/tooling/http_probe.py` | 0 | 见 4.2 |

**仓库原版 browser_real.py 没有跑**：它写死了 `args=['--no-sandbox']`（web/tests 下那份 browser.py 也一样），违反沙箱规则。为此在候选分支 `candidate/w17-live-acceptance-grokbot`（提交 `03ba941a973f14886815d57e53e00b874ec6ad29`，基于 3ae5166）上只改了 `tests_acceptance/W171/browser_real.py`：去掉 `--no-sandbox`，改用 `chromium_sandbox=True`；另外加了可选截图（环境变量 `W171_SHOTS`），断言一条都没改。diff 见 logs/04-candidate.diff（+7/−1）。

## 4. 分项结果

### 4.1 真实浏览器（真实 FastAPI 15971 + Vite 15972 + 有沙箱的 headless Chrome）：通过
browser_real.py 用 `page.route` + `route.fetch()` 取到**真实后端响应**，只推迟交给浏览器的时间，没有伪造数据。
| 项 | 结果 |
|---|---|
| CASE-A 只读策略显示；URL、顶栏、页面「当前案号」三处一致；有「本地自报角色，不是真实身份认证」提示 | 通过（截图 1） |
| 不回退到旧 `/access-policy` 接口 | 通过 |
| 点「刷新」时清空旧数据 | 通过 |
| 旧案 A 的延迟响应在切到 B 之后才送达，没有把 A 的数据恢复出来，B 正常显示 | 通过（截图 2） |
| 旧身份的延迟响应在切到 Public 之后才送达，没有恢复数据，显示拒绝提示 | 通过（截图 3） |
| 只有 GET 请求，没有页面错误 | 通过 |
| 截图时机 | 在对应断言通过、等 50ms 之后截 |

### 4.2 HTTP / SQLite（真实 uvicorn 进程，127.0.0.1，仓库外探针）：部分失败
| 项 | 结果 |
|---|---|
| 角色矩阵：LeadInvestigator / Investigator 读 CASE-A 得 200（saved），读 CASE-B 得 200（default），读不存在的案得 404；Public / ExternalExpert / InterestedState / AgentService 不管案件存不存在都是 403 FORBIDDEN，响应完全一样（不泄露案件是否存在） | 通过 |
| 成功和拒绝的响应都带 `Cache-Control: no-store` | 通过（18/18） |
| GET 不写库：18 次 GET 前后 `audit_events` 都是 0 行 | 通过 |
| **真跨线程并发**：端点读完策略后人为停 1 秒，另一个线程写 v2 策略和审计 → GET 返回 200 + v1 + 空事件（单一快照），写线程等了 1.04 秒后提交成功，再读一次得到 v2 + `version-2` | 通过 |
| **独立 API 验收 `test_policy_and_audit_are_one_snapshot`** | **失败**。根因：测试在请求处理线程内（monkeypatch 的 get_doc 里）同步开第二个连接去写；e40ae83 之后端点先执行 `BEGIN IMMEDIATE` 占住写锁，这个嵌套写等满 busy timeout（约 5 秒）后报 `database is locked`，异常冒出来变成 500。11-12 验收时用的是普通 `BEGIN`，冻结哈希不一致也正好说明了这处变化 |
| 独立 API 其余 13 项（角色拒绝、逐案审计权限、default/saved、no-store、GET 不建行、过滤与 0/49/50/51 条上限等） | 通过 |
| 访问相关回归 240 项 | 236 通过；**4 项失败**全在 `test_interviews_redaction.py`（11-11 初始导入时的旧测试）：完整笔录门禁（W5.2a / PR#28 之后）对它的默认请求返回 403，测试还按旧响应结构取 `turns` / `results` / `X-MCIS-Redaction`。这是已知的「旧测试没跟上新权限门」问题，跟 W17.1 工作台本身无关，但 W17 名下「字段级脱敏按角色」这一项在这个 SHA 上**没有可通过的测试** |

判定说明：快照不变量在真实并发下是成立的（写方被阻塞，不会混出两个版本），但 3ae5166 上仓库自带的验收用例确实失败，所以「服务」按实际结果记为**失败**。修法要么改测试（把写方放到另一个线程，断言不变），要么端点捕获锁超时；该怎么改需要 Dot / Mark 裁定，我没有改测试断言，也没有改产品。

### 4.3 模拟 DOM / API 替身（不算真实验收）
| 项 | 结果 |
|---|---|
| `web/tests/run-access-workbench-w171.sh`（node + renderToStaticMarkup，模型、渲染、传输） | 通过 |
| `web/tests/access-workbench-w171.browser.py` 的仓库外有沙箱副本（真 Chrome，但 API 全部由 `page.route` 替身返回） | 通过；截图 `screenshots/simulated-dom/access-default.png`。只能说明 UI 逻辑，不算后端验收 |

### 4.4 未验
- W17 的编辑、认证、导出脱敏、全系统字段脱敏：这个 SHA 上没有实现。
- 仓库原版 browser_real.py 和 web/tests 的 browser.py 原样运行：没跑，因为写死了 `--no-sandbox`。
- 多视口和移动端：W171 脚本没要求，也没另外跑。
- TypeScript 编译和 Vite 生产构建：没跑。
- Firefox / WebKit；有界面（headed）窗口。

## 5. 首个错误与复现
```
cd /workspace/mcis-w4-3ae5166/service   # HEAD 3ae5166
PYTHONPATH=. .venv/bin/pytest -q -p no:cacheprovider ../tests_acceptance/W171/test_workbench.py
FAILED ../tests_acceptance/W171/test_workbench.py::test_policy_and_audit_are_one_snapshot
E  AssertionError: {"code":"INTERNAL_ERROR","message":"请求处理失败"}   assert 500 == 200
根因（probe_snapshot.py）：sqlite3.OperationalError: database is locked（端点 BEGIN IMMEDIATE，引入于 e40ae83）
```

## 6. 文件
- logs/：00-env、00-frozen-hash-check/drift、01 API 验收与快照探针、02 回归与笔录门禁探针、03 web node、04 候选分支 SHA 与 diff、05 真实浏览器、06 模拟 UI、07 HTTP 探针 JSON
- screenshots/：1–3 是真实浏览器截图，simulated-dom/ 是替身截图
- tooling/：仓库外探针脚本（没有放进仓库）

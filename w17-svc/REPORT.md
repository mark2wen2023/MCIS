W17：服务失败（仓库回执 50/50 通过；真实 HTTP 独立补验 28/31，custody 端点向外部角色暴露 Restricted 证据元数据）；真浏览器未跑（本回执不含浏览器，见 Chromium 回执 29cbfe2）

# MCIS W17 服务回执 a80226d

- 执行时间：2026-11-25 11:37–11:45（北京时间，UTC+8）。执行环境是 Grok Bot 的 Linux 盒子，uid 1000。
- 本回执取代 #106 里基于 3ae5166 的 W17 结果。
- 数据全部合成：虚构案件 SYN-A / SYN-B，两案都用 EV-001，文件字节是编出来的。服务只监听 127.0.0.1，数据放在临时目录。
- 没改产品，没触发 CI，没合并，没部署，没碰三维仓库。本回执没有建候选分支。

## 1. 版本
| 项 | 值 |
|---|---|
| 工作树 | `/workspace/mcis-w17-svc-a80226d`（独立 `git worktree add --detach`；先用令牌请求头 fetch，成功） |
| HEAD | `a80226d7e32d79ce8ab7a035a16e5089bfbac377`（2026-11-25 07:05 +0800，"Pin synthetic W17 selection and registration acceptance"） |
| `git status --porcelain` | 运行前为空。pytest 的 `test_custody_jsonl_accepted_by_csharp_ledger` 会重新生成被跟踪的 `tools/mcis-compat/out/*.dll/.pdb`，所以跑完后那两个文件显示为修改；已用 `git checkout -- tools/mcis-compat/out` 还原，结束时为空 |
| 与 29cbfe2 的关系 | a80226d = 29cbfe2 + 只新增 `tests_acceptance/w17-evidence-selection-receipt/`（7 个文件），service/web/contracts 零差异 |
| W17 验收目录 | `tests_acceptance/w17-evidence-selection-receipt/`（README、run.cjs、pins.json、selection/receipt 的 .py/.tsx）。另有 `tests_acceptance/W171/`（旧 W17.1 工作台）。没有 `DEFECTS/W17*` |

## 2. 工具
Python 3.13.5，service/.venv 按 requirements 新建（fastapi 0.165.0、SQLAlchemy 2.1.9、pytest 9.2.0、httpx 0.28.1）；Node v24.22.1；`web/` 下 `npm ci`（React 19.3.1、react-router-dom、esbuild）。
**Happy DOM 21.0.4**：README 要求提供「已有的 Happy DOM」，盒子上原来没有，所以用 `npm i happy-dom` 装在仓库外的 `/workspace/w17-tools/node_modules`（安装日志 logs/00-happy-dom-install.log）。测试本身不下载任何东西。详见 logs/00-env.txt。

## 3. 命令与退出码（工作树根目录）
| # | 命令 | 退出码 | 结果 |
|---|---|---|---|
| 1 | `node tests_acceptance/w17-evidence-selection-receipt/run.cjs --source /workspace/mcis-w17-svc-a80226d --python /workspace/mcis-w17-svc-a80226d/service/.venv/bin/python --web-modules /workspace/mcis-w17-svc-a80226d/web/node_modules --happy-dom-entry /workspace/w17-tools/node_modules/happy-dom/lib/index.js` | **0** | `Verified 100 input Git blobs at 29cbfe2…`；`PASS 20 assertions`（selection）；`PASS 30 assertions`（receipt） |
| 2 | `cd service && PYTHONPATH=.:.. .venv/bin/pytest -q -p no:cacheprovider tests/test_evidence.py tests/test_evidence_intake_w42.py tests/test_access_workbench.py ../tests_acceptance/W171/test_workbench.py` | 1 | 136 passed，2 failed（见 4.3） |
| 2b | `cd service && PYTHONPATH=.:.. .venv/bin/python <报告>/tooling/probe_export.py` | 0 | `/export` 返回 409 ARCHIVE_RESTORE_UNSUPPORTED |
| 3 | `service/.venv/bin/python -B <报告>/tooling/e2e_server.py --repo . --data /tmp/w17a-data --port 18771 &`，然后 `service/.venv/bin/python -B <报告>/tooling/http_probe.py /tmp/w17a-data/ready.json` | probe **1** | 28/31 通过（见 4.2） |

## 4. 分项结果

### 4.1 仓库回执（README 原样）：通过，但**属于模拟 DOM + 进程内 ASGI**
README 自己写明：不启动 HTTP 监听，不启动浏览器。前端是真实的 EvidencePage 和 API 辅助函数跑在 **Happy DOM（模拟 DOM）** 里；后端是 FastAPI TestClient（进程内，没有网络监听），响应字节经子进程 IPC 传过去，SQLite 是临时库。
| 项 | 结果 |
|---|---|
| 100 个固定 blob 核对（29cbfe2） | 通过 |
| Selection 20 条断言：显式点选才读保管链；切案清空旧选择；迟到的列表响应不会回填；Public 拒绝时不返回选中证据 | 通过 |
| Receipt 30 条断言：真实 preview/commit 登记；显式点读取才显示回执；回执的案件、证据 ID、摘要、原件 SHA 一致；旧案迟到响应、错案/错摘要/错证据、撤销权限都不显示回执；库里最后只有 2 条 Register custody 和 2 条 audit，没有 Access | 通过 |

### 4.2 真实 HTTP + SQLite 独立补验（真实 uvicorn 进程，127.0.0.1:18771，create_app 全应用）：**28/31，失败 3 项**
种数据走真实 HTTP 的 `evidence-intakes:preview` / `:commit`。SQLite 用只读方式直接查询。
| 项 | 结果 |
|---|---|
| SYN-A / SYN-B 列表各只有自己的 EV-001（SOURCE-本案），不串案 | 通过 |
| 各自 custody 只有本案 1 条 Register | 通过 |
| `/evidence/EV-001/intake` 回执的 requestDigest、sourceSha256、fileName 与登记一致，`replayed=true`，不含 contentBase64 | 通过 |
| SYN-A 的摘要拿到 SYN-B 下查 → 404；EV-999 → 404；响应里都没有 sourceSha256 | 通过 |
| Public 访问 `/evidence`、`/evidence/EV-001`、`/intake`、`/custody` 全部 403，不带元数据 | 通过 |
| 外部角色（ExternalExpert / InterestedState / AgentService）：列表 200 但为空 `[]`（FR-05 Remove 生效）；单条 `/evidence/EV-001` 403；`/intake` 403 | 通过 |
| **外部角色读 `/evidence/EV-001/custody`** | **失败（3 个角色都是）**。返回 200，Register 事件的 `detail` 里有完整登记元数据：标题 `SOURCE-SYN-B`、文件名 `SYN-B.txt`、`"confidentiality":"Restricted"`、来源、sha256。默认策略 FR-05 写的是「Restricted 证据仅调查组可见，不对外部角色列出」，列表和单条都遵守了，custody 端点却只检查 `require(ctx,s,case_id,"evidence_meta")`（外部角色是 ReadOnly），没有经过 `filter_evidence`（`service/mcis_service/evidence/router.py` 第 115–120 行）。这属于 W17「字段级脱敏」的出口缺口，仓库回执没覆盖：它只测了 Public 和调查组。 |
| 改策略让 SYN-B 对 LeadInvestigator 为 Deny 后，读 intake 得 403，不出回执；SYN-A 不受影响 | 通过 |
| SQLite：所有读取结束后 custody 仍只有 2 行 Register（一案一行），没有 Access/Verify；GET 不增加 audit 行（seed 后 2 行，结束时还是 2 行） | 通过 |
所有响应都带 `Cache-Control: no-store`（抽查 intake 和列表）。

### 4.3 pytest（证据、登记、权限相关）：136 通过，2 失败
- `tests/test_evidence.py::test_custody_jsonl_accepted_by_csharp_ledger`：失败。原因是 `/export` 返回 409 `ARCHIVE_RESTORE_UNSUPPORTED`（「此案未通过完整恢复预检，未生成部分案件包」），测试把它当 zip 解析，报 BadZipFile。这是已知的导出/归档门禁问题，跟 W17 选择/回执无关。
- `tests_acceptance/W171/test_workbench.py::test_policy_and_audit_are_one_snapshot`：失败，返回 500 `database is locked`。根因和 3ae5166 上一样：端点用了 `BEGIN IMMEDIATE`，测试却在请求线程里同步写库。这是 W17.1 的旧用例。

### 4.4 真实浏览器
本回执不含浏览器（未跑）。真实 Chromium 的结果见单独的 Chromium 回执 29cbfe2；两个 SHA 的产品文件完全一致。

### 4.5 未验
- 生产认证：角色是自报的请求头。
- 原件下载与 Access 写入：本回执刻意不下载。
- 归档路径。
- custody 泄露在 UI 里是否可见：EvidencePage 对外部角色列表为空，点不到行，所以没测。
- 全量 service 回归没跑。

## 5. 首个错误与复现
```
cd /workspace/mcis-w17-svc-a80226d
service/.venv/bin/python -B /workspace/mcis-w17-svc-report/tooling/e2e_server.py --repo . --data /tmp/w17a-repro --port 18771 &
curl -s -H 'X-MCIS-Role: ExternalExpert' -H 'X-MCIS-Operator: x' http://127.0.0.1:18771/api/v1/cases/SYN-B/evidence            # -> []
curl -s -H 'X-MCIS-Role: ExternalExpert' -H 'X-MCIS-Operator: x' http://127.0.0.1:18771/api/v1/cases/SYN-B/evidence/EV-001/custody  # -> 200，detail 含 SOURCE-SYN-B / SYN-B.txt / Restricted
```
仓库回执（命令 1）本身没有报错。

## 6. 文件
- `logs/`：00 环境与安装；01 仓库回执的 stdout/stderr/退出码；02 pytest 与导出探针；03 真实 HTTP 探针的 JSON（逐项结果、custody 行、截断的响应开头）和 uvicorn 日志。
- `tooling/`：e2e_server.py（合成后端，只在测试时用的延迟和 denyB 控制）、http_probe.py、probe_export.py，都在仓库外。
- `screenshots/`：空。本回执没有真实浏览器，Happy DOM 不能截图。

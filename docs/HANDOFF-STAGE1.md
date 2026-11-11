# MCIS 阶段性交接（第一阶段，2026-11-11 22:30 北京时间）

> 读者：接手本仓库的 OpenAI Codex（单一代理）。
> 本文所有状态、数字都来自仓库文件，括号里写了出处（`文件:行号` 或节名）。和仓库文件冲突时，**以仓库文件为准**，并请顺手改正本文。
> 旧的 `HANDOFF.md`（约 21:50 快照）保留作历史，内容已被本文覆盖。
> 交接时所在提交：`3e42024`（2026-11-11 22:18 +0800）之上，另有未提交改动（见 §11）。

---

## 0. 第一件事

1. 按 §3 建环境，跑一遍 §3.6 的基线，和本文 §3.7 的数字对比。对不上先查原因，再动代码。
2. 读 `ROADMAP.md` 文末状态表（按时间追加，**同一包以最后一行为准**）和你要做的包的 `DEFECTS/<包>.md` **文末裁定**。
3. 按 §8 的顺序干活。

---

## 1. 项目目标与产品定位

- 这是 Mark Wen 的 WMU 硕士论文项目：**海事事故调查仿真系统 MCIS（MCIS-3D）**，依据论文《Design and application research of maritime casualty investigation simulation based on Unity 3D》（`README.md` 首段，`thesis.txt`）。
- 目标：Unity 3D 回放与推演 + 调查工作台，做成**完整、接近游戏体验、高端 UI**的系统；**原型里出现的每一个 UI 功能都要实现**（`HANDOFF.md` §1；`ARCHITECTURE.md` §1.1「把调查仿真做成一款好用的游戏」）。
- 部署定位（交接前 Mark 提出“真实的部署可用”，架构建议，尚未写进 ROADMAP，见 §7）：**内网联机版为正式产品**，另做**离线单机现场版**，两者**同一代码库**（`HANDOFF.md` §8）。
- 页面目标：原型 17 页（01–08 在 `prototype/index.html`，09–17 在 `prototype/p6/`），各包与原型页的对应见 `ROADMAP.md:17-41`。

---

## 2. 架构与目录

### 2.1 分层（`HANDOFF.md` §1；`contracts/CONTRACTS.md`）

| 层 | 位置 | 要点 |
|---|---|---|
| Unity 三维 | `unity/` | Unity 6（6000.0.x LTS）+ URP 17，C# 9；Cesium for Unity（可选，`MCIS_CESIUM` 宏，未装回退 ENU）、Dynamic Water 2（`Scripts/Integrations/Dwp2`）、Enviro 3（`Scripts/Integrations/Enviro`）、AIS（`Scripts/Domain/Ais`）。见 `unity/INTEGRATION.md` §1。与工作台联调是 W13，未开始。 |
| 纯 C# 计算核心 | `unity/Assets/_Project/Scripts/{Core,Data,Domain,Simulation,…}` | **netstandard2.1、C# 9、不得引用 UnityEngine**。CPA/DCPA、COLREG、VDR/时间轴、笔录比对、系统分析、工休、What-if 的权威实现都在这里。各包有独立 xUnit 工程 `unity/Tests_*`、`unity/DotnetTests*`。 |
| mcis-core CLI | `tools/mcis-core/` | glob 引用上面的 Scripts，不复制源码。子命令 `cpa`、`align`、`colreg`；stdin/stdout JSON；领域错误放在信封错误码里，**进程退出码 4**（`DEFECTS/W2.md:415-420` 第 1、2 条）。包装脚本 `tools/mcis-core/mcis-core.sh` 在源码变了时自动 Release 构建到 `tools/mcis-core/out/`（不入库）。基线哈希 `logs/mcis-core-hashes-2106.txt`。 |
| 调查服务 | `service/` | FastAPI + SQLite，**只监听 127.0.0.1:8765**（`service/mcis_service/config.py:20`）。案件、审计（哈希链 JSONL）、脱敏网关、`.mcase`、调用 mcis-core、报告。 |
| Web 工作台 | `web/` | Vite + React + TypeScript + ECharts，只通过服务 HTTP 读写。服务地址由 `vite.config.ts` 用 `MCIS_API` 注入 `__MCIS_API__`（`web/vite.config.ts:5,11`；`web/src/config.ts`）。 |
| 合同 | `contracts/` | 模块之间唯一接口真相源：`openapi.yaml`、`schemas/*.json`（18 个）、`CONTRACTS.md`、`gisis-mapping.md`（W16.1 新增）。 |

### 2.2 目录速查

```
AGENTS.md            给代理的简短规则（先读本文）
ROADMAP.md           包定义（:17-41）+ 状态表（:46 起，按时间追加）
REQUESTS.md          合同外提案、跨包改动登记、各包进度段（文末 22:25「W16 进度」）
DEFECTS/<包>.md      缺陷单 + 架构裁定（文末为最新）
P6A_PLAN.md          通用规则、真实报告口径（:16）
ARCHITECTURE.md      Unity 工程架构、需求追溯、.mcase schema
contracts/           openapi.yaml、schemas/、CONTRACTS.md、gisis-mapping.md
service/             mcis_service/（analysis colreg reports interview_compare audit …），tests/
web/                 src/（pages/ reports/ interview/ styles/<pkg>.css），tests/
tools/mcis-core/     CLI；tools/shoot_web*.sh 截图脚本
unity/               Scripts + Tests_W1/W2/W3/W5/W14/W15/W18 + DotnetTests/DotnetTests2 + Tests_W11_Ecfc（空）
tests_acceptance/    独立验收：C#（W1 W2 W3 W5 W14 W15 W18 W1_realref）、Python（W6 W12）
prototype/           原型：index.html（01–08）、p6/s09_11.html s12_14.html s15_17.html（09–17）
screenshots/         原型截图 01–08（1920），1440/01–17；实现截图 20-colreg* 30-analysis* w16/
reports/             公开事故报告结构化数据：haili5/、yangze22/、REAL_CASES.md（真实基准）
samples/             虚构 Lily/Mary 演示材料
logs/                冻结哈希、自测/验收日志（保留，不要删）
fonts/               报告用 Noto Sans SC
```

- 运行时数据 `service/data/`（含 `mcis.db`）首次启动自动建，已 `.gitignore`（`.gitignore:45`）。
- W12 分析种子 `service/mcis_service/analysis/data/w12-analysis-seed.json` + `.sha256`，**必须保留**，只能用 `build_seed.py` 重生成（`ROADMAP.md:138`）。
- 虚构演示种子 `service/mcis_service/seed/lily_mary.py`。

---

## 3. 环境搭建与测试命令

交接机实测版本：dotnet SDK **8.0.428**（`~/.dotnet/dotnet`），Python **3.13.5**（`service/.venv`），Node **v24.22.1** / npm **11.21.1**。

### 3.1 .NET

```bash
export PATH="$HOME/.dotnet:$PATH" DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
# 各包自测
dotnet test unity/Tests_W1_Colreg/Mcis.W1.Colreg.Tests.csproj
dotnet test unity/Tests_W2_Vdr/Tests_W2_Vdr.csproj
dotnet test unity/Tests_W3_Inv/Tests/W3.Inv.Tests.csproj
dotnet test unity/Tests_W5_Interview/Tests/W5.Interview.Tests.csproj
dotnet test unity/Tests_W14_WhatIf/Tests_W14_WhatIf.csproj
dotnet test unity/Tests_W15_Sys/Tests/W15.Sys.Tests.csproj
dotnet test unity/Tests_W18_HF/Tests/W18.HF.Tests.csproj
dotnet test unity/DotnetTests/Tests/Mcis.Pure.Tests.csproj
dotnet test unity/DotnetTests2/Tests/Mcis.Pure.Tests.csproj
# 独立验收
dotnet test tests_acceptance/W1/W1.Acceptance.csproj     # 同理 W2 W3 W5 W14 W15 W18
dotnet run  --project tests_acceptance/W1_realref/W1.RealRef.csproj   # 真实案例参考运行（控制台程序，不计通过率）
# LibCheck（netstandard2.1、无 UnityEngine）
dotnet build unity/Tests_W2_Vdr/LibCheck/W2.LibCheck.csproj
dotnet build unity/Tests_W14_WhatIf/LibCheck/W14.LibCheck.csproj
# mcis-core
echo '<json>' | ./tools/mcis-core/mcis-core.sh cpa      # 或 align / colreg；首次自动构建
```

注意：W14 的测试会重写已入库的 `logs/w14-clearance-sat-vs-true.csv`、`logs/w14-scenario-dump.json`；`W1_realref` 会重写 `logs/w1.1-retest-realcases.txt`。跑完用 `git status` 看一下，只是测试产物的话 `git checkout -- <文件>` 还原，别误提交。

### 3.2 服务

```bash
cd service
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt     # fastapi uvicorn sqlalchemy pydantic python-docx reportlab jsonschema pyyaml pytest httpx …
.venv/bin/pytest -q -p no:cacheprovider       # 全量；必须用 service/.venv
.venv/bin/python -m mcis_service              # 启动，host 写死 127.0.0.1，端口 MCIS_PORT（默认 8765）
```

环境变量（`service/mcis_service/config.py:14-20`）：`MCIS_DATA_DIR`（默认 `service/data`）、`MCIS_DB_URL`、`MCIS_SEED_DEMO`（默认 1，写入虚构 Lily/Mary）、`MCIS_CORE`（默认 `tools/mcis-core/mcis-core.sh`）、`MCIS_CORE_TIMEOUT`（默认 60 s）、`MCIS_PORT`。测试夹具用临时目录，不碰 `service/data`（`service/tests/conftest.py`）。

### 3.3 Web

```bash
cd web
npm install --no-audit --no-fund
npx tsc -b --force
npm test                         # colreg-render 18 + colreg-w61（W6.1+W6.2）58
npm run test:w5                  # 询问比对页
npm run test:w16                 # 报告页
bash tests/run-analysis-w12.sh   # 分析页
npm run lint                     # oxlint
```

`web/tests/.tmp-*.cjs` 是 esbuild 临时产物，已忽略（`.gitignore:21`）。

### 3.4 Python 验收（W6、W12）

```bash
cd tests_acceptance/W12 && ../../service/.venv/bin/pytest -q -p no:cacheprovider
cd tests_acceptance/W6  && ../../service/.venv/bin/pytest -q -p no:cacheprovider   # 含浏览器用例 I1（需 chrome/chromium），写 screenshots/runs/<时间戳>/
```

两者都用临时端口和临时数据目录，不碰 8765 和 `service/data`（`tests_acceptance/W12/conftest.py` 头注释；`tests_acceptance/W6/test_w6_e2e_browser.py:3`）。

### 3.5 一键开发

```bash
./run_dev.sh              # 后端 127.0.0.1:8765 + Vite 127.0.0.1:5173（MCIS_API 自动设为后端地址）
./run_dev.sh --preview    # 先 build，再 vite preview :4173
```

截图：`tools/shoot_web.sh`、`tools/shoot_web_w6.sh`、`tools/shoot_web_w12.sh`。

### 3.6 交接时基线（2026-11-11 22:20–22:30 在交接机实跑，未改任何实现或测试）

| 项目 | 结果 | 说明 |
|---|---|---|
| Tests_W1_Colreg | 1802/1802 | |
| Tests_W2_Vdr | 309/309 | |
| Tests_W3_Inv | 254/254 | 含 W5.1 新增 W51Tests |
| Tests_W5_Interview | 83/83 | |
| Tests_W14_WhatIf | 115/115 | |
| Tests_W15_Sys | 125/125 | |
| Tests_W18_HF | 92/92 | |
| DotnetTests | 63/63 | |
| DotnetTests2 | 84/84 | |
| 验收 W1 | 151/151 | |
| 验收 W2 | 298/298 | |
| 验收 W3 | **185/186** | 败 `W31RetestAcceptanceTests.ToJson_CamelCaseKeys_IncludesConfirmedInBatch_MatchesSchemaPropertySet`：W5.1 新增可选字段 `statementVersion`。按 `DEFECTS/W3.md:421-422` 裁定改写断言为“允许新增可选字段”，随 W5.1 验收处理。**不是回归。** |
| 验收 W5 | 47/47 | W5.1 的 D01/D02 已过 |
| 验收 W14 | **69/70** | 败 `W14_2RetestTests.NarrowValleyShorterThanCoarseStep_IsDocumented`：KnownDefect W14-D06，归 W14.3（`DEFECTS/W14.md:264-283`）。 |
| 验收 W15 | 112/112 | |
| 验收 W18 | **96/97** | 败 `RetestW181AcceptanceTests.W18_D08_EdgeWindow_AbsorbedIntoAdjacentViolationGroup`：KnownDefect W18-D08，归 W18.2（`DEFECTS/W18.md:233-253`）。 |
| W1_realref（参考运行） | 正常结束 | YANGZE 22：`VERDICT yangze22: ACCEPTABLE (VEGA not give-way)` |
| mcis-core 构建 | 0 错误 | |
| service 全量 pytest | **283/283** | 含 `test_reports_w16.py` 42 项 HTTP 用例（Codex 在沙箱里没跑成，`REQUESTS.md` 22:25 段“还差 1”，这里已跑通） |
| 验收 W12（Python） | 18/18 | 含 2348 点 cpa 重算 |
| 验收 W6（Python，排除 I1 浏览器 4 项） | **75 过 / 35 败**（114 项） | 35 败全部是裁定导致的旧用例（PATCH 仍用 `reviewStatus/note`，F1 断言不含 `runId`），须按 `DEFECTS/W6.md:141-144` 改写。与 `ROADMAP.md:134` 的 79/114（含 I1 4 项）一致。 |
| web `tsc -b --force` | 0 错误 | |
| web `npm test` | 18 + 58 断言通过 | |
| web `test:w5` | 38 断言通过 | |
| web `test:w16` | 140 断言通过 | W16.1 版 |
| web `run-analysis-w12.sh` | 94 通过 | |
| web lint（oxlint） | 0 错误，5 条警告 | Toast.tsx、ReportPage.tsx ×2、ReportView.tsx ×2（react 规则警告） |

### 3.7 冻结哈希现状（交接时用 `sha256sum -c` 核对）

| 清单 | 条目 | 不符 | 解读 |
|---|---|---|---|
| `logs/w16-impl-hashes-frozen.txt` | 26 | 16 不符 + 1 已删（`ColregDraftButton.tsx`） | 预期：W16.1 已在其上改代码但**没重新冻结**（`REQUESTS.md` 22:25「W16 进度」）。验收以 W16.1 为准，先重新冻结。 |
| `logs/w6.2-impl-hashes-frozen.txt` | 36 | 1：`web/src/pages/RecommendationsPage.tsx` | W16.1 裁定 8 在 `#/recs` 页头加了报告入口（`REQUESTS.md` W16.1 实现说明；`DEFECTS/W16.md:10`）。验收 W6.2 时对此文件按 W6.2 片段核对。 |
| `logs/w12.1-impl-hashes-frozen.txt` | 31 | 0 | |
| `logs/w5.1-impl-hashes-frozen.txt` | 30 | 0 | 共享文件（openapi.yaml、audit-event.schema.json、main.py、main.tsx、routes.ts、package.json）以后再变，按 W5 片段核对（该文件头注释）。 |

---

## 4. 开发流程与规则

### 4.1 包化开发

- 包号与内容：R0（P0）、R1（W1–W3）、R2（W4–W7）、R3（W8–W13）、R4（W14–W17）、R5（W18–W20）、R6（W21），见 `ROADMAP.md:17-41`。小修包用后缀（W6.1、W6.2、W18.2…）。
- 流程（`ROADMAP.md:10-15`，补充规则 `ROADMAP.md:57-58`、`:98`）：
  1. 实现 + 自测通过。
  2. 在 `ROADMAP.md` 状态表**追加**一行「待测」，**必须附冻结哈希**（文件清单 + sha256，放 `logs/<包>-impl-hashes-frozen.txt`）。冻结后不改这些文件。
  3. 独立验收：测试写在 `tests_acceptance/<包>/`，缺陷写 `DEFECTS/<包>.md`；还没修的缺陷用例标 KnownDefect（C# `[Trait("Category","KnownDefect")]`，Python `@pytest.mark.knowndefect`）。验收方不改实现。
  4. 架构裁定（写在 `DEFECTS/<包>.md` 文末）→ 返工 → 复测，直到清零或裁定延期。
  5. **断言和裁定冲突时改写断言，不删用例。**
  6. 「已验收」后才推进依赖它的下游包。
- 冻结清单：被测路径上用到的 `Domain/Evidence` 和 `tools/mcis-core/src` 也要列入（`DEFECTS/W2.md:415-420` 第 4 条）。
- 共享入口文件 `web/src/main.tsx`、`web/src/routes.ts`、`web/src/styles.css` **不进单包冻结清单**；各包样式写 `web/src/styles/<包>.css` 由入口引入（`DEFECTS/W12.md:64-67`；`DEFECTS/W6.md:134-140`）。共享文件（`service/mcis_service/main.py`、`contracts/openapi.yaml`、`web/package.json` 等）按本包片段核对。
- 要改别的包已冻结的文件，**先在 `REQUESTS.md` 登记**（`ROADMAP.md:44`；`AGENTS.md`）。
- 合同先行：改接口先改 `contracts/`（或在 `REQUESTS.md` 提案），再实现。新路由暂不入合同时用 `PENDING_CONTRACT=True`/`include_in_schema=False`，入合同后 `service/tests/test_contracts.py::test_openapi_yaml_matches_routes` 必须通过。

### 4.2 硬约束

- 服务、前端**只绑 127.0.0.1**。
- 不打印、不提交、不外发任何密钥或 `.env`。
- 不碰 `/workspace/yuehai-*`。
- 不 `git push`，除非仓库主人 Mark 当次明确要求。
- 纯 C# 核心：C# 9、netstandard2.1、无 UnityEngine；Unity 侧 C# 9 规范（无 file-scoped namespace、record、required/init）（`unity/INTEGRATION.md` §1.1）。
- 阈值：Domain 层用 double + 容差 `1e-6`；tick 只用于时间解析。验收时“正好等于门限”用 ±1e-7 扰动，“明显超过”用 ≥1e-5（`DEFECTS/W2.md:415-420` 第 3 条）。
- CLI：格式/缺字段用 BAD_REQUEST；领域错误用领域码（如 `conflict_case_id_invalid`），退出码一律 4。
- 页面必须有“仅作技术分析，不作责任认定”类声明的地方保留（W6 `ROADMAP.md:102`；W16 PDF/DOCX 水印 `ROADMAP.md:132`）。

---

## 5. 数据口径

- **真实报告可直接用**：Mark 上传的事故报告（`reports/`，目前是海力5 / WAN HAI A17 和 YANGZE 22 / VEGA DREAM）都是公开资料，真实数据和信息可直接用于演示、测试和基准（`P6A_PLAN.md:16`；`ROADMAP.md:44`、`:89`；`HANDOFF.md` §5）。基准见 `reports/REAL_CASES.md`。
- 每个值都要标**来源**（报告页码/图号/条目）和**【直接】/【推算】/【估计】**。例：航向当作对地航向标【推算】（`DEFECTS/W12.md:64-67`），GNSS 天线位置标【估计】（`ROADMAP.md:104`）。
- **Lily/Mary 演示案是虚构**（星屿港，14:15–14:27，Mary 撞 Lily 左舷；`P6A_PLAN.md:16`），页面和数据必须标「虚构」/「示例数据（虚构）」。重算值为准：14:17 两船距离 2.4 nm、DCPA < 0.1 nm，原型上的 5.1 nm/0.22 nm 自相矛盾已作废（`ROADMAP.md:68`）。
- **YANGZE 22 caseId = `CJK-2024-1230-YangZe22-VegaDream`**（`reports/yangze22/case.json`；`DEFECTS/W12.md` 第 6 条；`ROADMAP.md:135`、`:138`）。占位 `CASE-REAL-YANGZE22` 已废弃。海力5 caseId `CASE-2025-HAILI5-WANA17`（`tests_acceptance/W12/conftest.py`）。
- **真实案例在报告模块的锁已可解除**：W16/W16.1 目前对海力5、YANGZE 22 的报告生成/导出/快照仍返回 `409 report_real_data_pending`，W14 来源只读虚构条目（`ROADMAP.md:132`、`:135`；`REQUESTS.md` 22:20、22:25 段）。原因是 `DEFECTS/W16.md:8` 要求“以 Mark 本人在 Codex 对话里确认为准”。**交接时总负责方（Grok Bot）转告：Mark 已在 Codex bot 对话里亲自确认 `reports/` 里的报告可以用。** 所以 `REQUESTS.md` 22:25「W16 进度」里那几项“等 Mark 确认”**已经解除，接手后直接做**：
  1. 中国海事模板章节标题逐字采用 `reports/haili5`、`reports/yangze22` 原文（含责任认定类章节；`DEFECTS/W16.md:5`），去掉 TODO/`pendingRuling` 标签。
  2. W14 的海力5 / YANGZE 22 真实条目进入报告的 whatif 来源（仍从 W12 种子读，带哈希自检）。
  3. YANGZE 22 导入服务数据库（`DEFECTS/W16.md:8` 已同意，作为一个新包）。
  4. 放开 `409 report_real_data_pending`：真实案例可生成/导出/取快照，所有真实值带来源和【直接】/【推算】/【估计】。
  仓库里目前还没有这条确认的书面记录，接手第一天请在 `ROADMAP.md` 追加一行「口径 · 更新 · Mark 在 Codex 对话确认 reports/ 可用于 W16 真实案例」。

---

## 6. 全部包状态总表

状态词：已验收 / 有条件通过（主体通过，留小包）/ 待验收（已交付已冻结，等独立验收）/ 进行中未冻结 / 未开始。

| 包 | 内容 | 原型页 | 状态 | 未关缺陷 / 遗留 | 下一步 | 关键文件 | 出处 |
|---|---|---|---|---|---|---|---|
| P0 | 平台骨架：contracts、服务骨架、web 骨架、mcis-core cpa | — | 已验收 | — | — | `contracts/` `service/` `web/` `tools/mcis-core/` | `ROADMAP.md:63` |
| W1（含 W1.1） | COLREG 规则引擎；mcis-core colreg；服务 evaluate | 11 | 已验收 | — | — | `Scripts/Domain/Colreg` `unity/Tests_W1_Colreg` `tests_acceptance/W1` | `ROADMAP.md:95-96`；`DEFECTS/W1.md:301` |
| W2（W2.1–W2.3） | VDR 导入、多轨时间轴、钟差、冲突检测；mcis-core align | 09 | 已验收（系列结案） | — | — | `Scripts/Data/Vdr` `Scripts/Domain/Timeline` | `ROADMAP.md:113`；`DEFECTS/W2.md:415-420` |
| W3（W3.1/W3.2） | 询问笔录交叉比对、安全建议、证据保管链 | 10 15 09 | 已验收（系列结案） | 验收 W3 1 项断言待改写（statementVersion，随 W5.1） | 验收 W5.1 时改写 | `Scripts/Domain/{Interview,Recommendations,Evidence}` | `ROADMAP.md:123`；`DEFECTS/W3.md:416-422` |
| W4 | 证据中心页（VDR 多轨回放、保管链、钟差/冲突） | 09 | 页面主体由 P0 完成 | 未接通 W2 align | 接 `POST /api/v1/core/align` 结果到页面 | `web/src/pages/EvidencePage.tsx` | `ROADMAP.md:64`、`:99` |
| W5 核心 | 询问笔录比对纯 C# 核心 | 10 | 有条件通过（45/47） | D01/D02 已在 W5.1 实现 | 随 W5.1 验收关闭 | `Scripts/Domain/InterviewCompare` | `ROADMAP.md:124`；`DEFECTS/W5.md:69-75` |
| W5.1 + W5 页面 | statementVersion/stale、Resubmit→Superseded、x-batchId、Submit 审计失败；service `interview_compare`（6 路由入 openapi）+ web 第 10 页（虚构） | 10 | **待独立验收**（无半成品） | 实现方自报 W5 验收 47/47、W3 验收 185/186 | 独立验收：核冻结 30 项；改写 W3 那 1 项断言；对照原型 10 截图 | `logs/w5.1-impl-hashes-frozen.txt` `service/mcis_service/interview_compare/` `web/src/interview/` `web/src/pages/InterviewPage.tsx` | `ROADMAP.md:140` |
| W6 / W6.1 | 避碰规则对照页（service colreg + web） | 11 | W6.1 有条件通过（112/114） | D06/D07 → W6.2 | — | `service/mcis_service/colreg/` `web/src/pages/ColregPage.tsx` | `ROADMAP.md:128`；`DEFECTS/W6.md:134-140` |
| W6.2 | evaluate 返回 runId；扩展路由入 schema；PATCH 只收合同字段；EvidencePage/RecommendationsPage 读 `__MCIS_API__`；1440 下判定表上移 | 11 | **待验收** | 验收前须改写 35 项旧用例 | 按 `DEFECTS/W6.md:141-144` 改写（32 项 PATCH 用合同字段，A5 仍 404、A6 仍 403；F1 比较时排除 runId），再验收 | `logs/w6.2-impl-hashes-frozen.txt`（RecommendationsPage.tsx 已被 W16.1 改，按片段核） `tests_acceptance/W6/` | `ROADMAP.md:134`、`:136` |
| W7 | 安全建议看板 + 征求意见轮次 | 15 | 页面主体由 P0 完成 | UpdateDraft 已在 W3.1 落地 | 按原型 15 补齐征求意见轮次 UI | `web/src/pages/RecommendationsPage.tsx` | `ROADMAP.md:64`、`:84` |
| W8 | 大厅 + 案件管理（.mcase 导入导出、完整性校验） | 01 02 | 未开始 | — | 规格→实现 | `Scripts/Data/CasePackage`（已有纯逻辑） | `ROADMAP.md:28` |
| W9 | 船舶参数 + 环境参数 | 03 04 | 未开始 | — | — | — | `ROADMAP.md:29` |
| W10 | 航迹编辑（AIS 导入、清洗、手绘） | 05 | 未开始 | — | — | `Scripts/Domain/{Ais,Tracks}`（已有纯逻辑） | `ROADMAP.md:30` |
| W11 | ECFC 编辑器（表 4 校验、自动布局） | 07 | 未开始（曾开工即暂停，只有空目录） | — | 从纯 C# 核心开始 | `Scripts/Domain/EcfcEditor`（空） `unity/Tests_W11_Ecfc/Tests`（空） | `ROADMAP.md:121`、`:125` |
| W12 | 分析页（D/DCPA/TCPA 曲线、关键时刻、W14 对比、天线敏感性） | 08 | 有条件通过（17/18） | D01【推算】→ W12.1 | — | `service/mcis_service/analysis/` `web/src/pages/AnalysisPage.tsx` | `ROADMAP.md:133`；`DEFECTS/W12.md:64-67` |
| W12.1 | 【推算】标注；analysis 两接口入 schema；YANGZE 22 caseId | 08 | **待验收** | 实现方自报 W12 验收 18/18；交接基线也是 18/18 | 独立验收：核冻结；复核 seed 数值未变、.sha256 一致 | `logs/w12.1-impl-hashes-frozen.txt` | `ROADMAP.md:138-139` |
| W13 | 仿真主界面：Unity 回放 + HUD + 与服务时间同步 | 06 | 未开始 | — | 见 §8 第 6 项 | `unity/Assets/_Project/Scripts/{Presentation,UI,Simulation}` `unity/INTEGRATION.md` | `ROADMAP.md:33` |
| W14（W14.1/W14.2） | What-if 反事实仿真核心 | 12 | 已验收 | D06 窄谷漏检 → W14.3 | — | `Scripts/Simulation/WhatIf` | `ROADMAP.md:116`；`DEFECTS/W14.md:278-283` |
| W14.3 | 粗扫改积分步长 dt，局部极小和转首率超阈值处加密 | 12 | 未开始 | 验收 W14 中 1 项 KnownDefect | 0.2 s 窄谷与 0.01 s 暴力扫描差 ≤ 0.1 m | 同上 | `DEFECTS/W14.md:278-283` |
| W14 页面 | What-if 页面（web + Unity 对比视图） | 12 | 未开始 | — | — | — | `ROADMAP.md:34` |
| W15（W15.1/W15.2） | 系统分析核心：Bow-tie / AcciMap / STAMP | 14 | 已验收（系列结案） | 页面未做；`contracts/schemas/systemic.schema.json` 未写 | 先写 schema，再做页面 | `Scripts/Domain/Systemic` | `ROADMAP.md:129`；`DEFECTS/W15.md:204` |
| W16 | 报告：IMO/MAIB/中国海事 × 中/英/双语、GISIS、PDF/DOCX、引用、Draft+审计、colreg 章节草稿后端 | 15 | **待验收**（22:04 冻结版，但已被 W16.1 改过） | 裁定 1–8 见 `DEFECTS/W16.md:2-11` | 直接以 W16.1 为准验收 | `service/mcis_service/reports/` `web/src/reports/` `contracts/schemas/report.schema.json` | `ROADMAP.md:135`、`:137` |
| W16.1 | 按 22:10 裁定：GISIS 对照表 `contracts/gisis-mapping.md`；W14 读 W12 种子；audit-event 可选 `snapshotRef` + 快照接口；删 ColregDraftButton；页头生成按钮 | 15 | **进行中未冻结**（代码改了大半，未标待测、未重新冻结） | 还差：重拍 `screenshots/w16/`、重算冻结（旧版另存）、ROADMAP 标待测；中国海事原文标题、真实条目、放开 409（口径已解除，见 §5）；GISIS Table 5 等级对应“待核” | 见 §8 第 2 项 | 改动清单见 `REQUESTS.md` 22:25 段；备份 `/workspace/w16-backup/` | `REQUESTS.md:242` 起 |
| W17 | 权限矩阵 + 字段级脱敏 + 访问审计 | 17 | 未开始 | W16 报告暂只开放 LeadInvestigator/Investigator（`DEFECTS/W16.md:7`）；analysis 只读接口无角色校验，归 R7 | — | `contracts/schemas/access-policy.schema.json` `service/mcis_service/redaction/` | `ROADMAP.md:37` |
| W18（W18.1） | 人为因素：HFACS、STCW/MLC 工休、疲劳、BRM（纯 C# 核心） | 13 | W18.1 有条件通过（94/95） | D08 → W18.2 | — | `Scripts/Domain/HumanFactors` | `ROADMAP.md:130`；`DEFECTS/W18.md:250-253` |
| W18.2 | D08：被记录首尾截断的休息段所涉窗口必须在报告中可见；Assumptions 补写 | 13 | 未开始 | 验收 W18 中 1 项 KnownDefect | 见 §8 第 5 项 | 同上 | `DEFECTS/W18.md:250-253` |
| W18 页面 | 人为因素页面 | 13 | 未开始 | — | — | — | `ROADMAP.md:60`（“web 部分未做”） |
| W19 | 知识库：相似案例检索、事故分级与通知义务 | 16 | 未开始 | — | — | — | `ROADMAP.md:39` |
| W20 | 智能体：报告抽取 6 智能体 + 人工确认队列（本地/国产模型） | 全局 | 未开始 | — | — | `service/mcis_service/agents/`（骨架） `contracts/schemas/agent-draft.schema.json` | `ROADMAP.md:40` |
| W21 | Unity↔工作台联调、Windows exe 打包、演示数据统一、用户手册 | 全部 | 未开始 | — | — | — | `ROADMAP.md:41` |

---

## 7. 关键结果（有文件依据）

- **W14 YANGZE 22 情景**（`DEFECTS/W14.md:241-245`；`logs/w14.2-fix-summary.md:39-42`；W12 复核 `DEFECTS/W12.md:36`）：

  | 情景 | 结论 | 数值 |
  |---|---|---|
  | S0 重建基线 | 碰撞 | 22:02:00.12（比报告晚 6.1 s），碰撞角 69.0°，VEGA DREAM 船首撞 YANGZE 22 右舷，距船首约 96 m |
  | Y1 | 险情（临界） | 184.35 m（安全线 185.2 m；天线敏感性区间 183.2–185.5 m） |
  | Y5（VEGA DREAM 应急抛锚） | 无碰撞 | 238.75 m |
  | Y1 + Y5 | 无碰撞 | 292.45 m |
  | Y4（全速倒车） | 险情 | 29.81 m |

  虚构 Lily/Mary：S1 130.4 m、S3 58.8 m 仍是险情；S0、S2 判船首对船首（`ROADMAP.md:104`、`:112`）。
- **W2 对齐**（`ROADMAP.md:99`）：虚构 Lily/Mary 12 条冲突，钟差 +3.200 s / −1.500 s；YANGZE 22 报告片段 31 行 / 7 条冲突；畸形输入 6 项均退出码 4。YANGZE 22 的时间源与应得冲突见 `reports/REAL_CASES.md` §2.2。
- **W12 重算**：三案例 D/DCPA/TCPA 共 2348 点用 mcis-core cpa 独立重算偏差 0；W14 导出与复测留档 52 值偏差 0（`ROADMAP.md:133`、`:138`；`DEFECTS/W12.md:36`）。W12.1 重跑 seed，14539 个数值逐个相等（`ROADMAP.md:138`）。
- **W1 真实案例**：海力5 19:51:15 起 NUC，按 R18 与报告第 8 条认定一致；YANGZE 22 判 VEGA DREAM 不是让路船（`ROADMAP.md:78`、`:95`；交接基线 `W1_realref` 输出同）。
- **W18.1**：220 组随机排班与独立参考实现一致；每天 6+4、连续 10h 合规，最长段 5h59m 报 LongestRest（`ROADMAP.md:126`、`:130`）。
- **W15**：真实案例 112/112（`ROADMAP.md:129`）。

---

## 8. 推荐的接手顺序（第一周）

每项完成后按 §4.1 流程追加 ROADMAP 行。

1. **跑基线（半天）**
   - 做：§3 全套。
   - 验收标准：数字和 §3.6 一致；只允许那 3 个 C# 失败（W3 1、W14 1、W18 1）和 W6 Python 的 35 项。
   - 额外：在 `ROADMAP.md` 追加 Mark 口径确认行（§5）。
2. **收口 W16.1（1–2 天）**
   - 做：
     1. 中国海事模板章节标题逐字取自两份原文（含责任认定类），删 TODO/`pendingRuling`。
     2. 真实案例放开 409：生成/导出/快照/whatif 条目对海力5、YANGZE 22 可用，值带来源和【直接】/【推算】/【估计】。
     3. 补 HTTP 用例和全量 pytest。
     4. 重拍 `screenshots/w16/`（1440/1920）。
     5. 旧冻结另存 `.v2.txt`，重算 `logs/w16-impl-hashes-frozen.txt`。
     6. ROADMAP 标「W16.1 待测」。
   - 验收标准：
     - service 全量 pytest 全绿；`test:w16` 通过；tsc 0 错误；`test_openapi_yaml_matches_routes` 通过。
     - YANGZE 22 用规范 caseId，报告每个真实数值有来源标注。
     - GISIS 必填按通函星号，无法确认的仍标「待核」，不自拟。
   - YANGZE 22 入库另开一包（例如 W16.2 或 W8 前置），做法同上。
3. **独立验收 W6.2、W12.1、W5.1+W5 页面（1–2 天）**，按 §9 的隔离做法。
   - W6.2：先按 `DEFECTS/W6.md:141-144` 改写 35 项（不删）。验收标准：114 项除裁定延期外全过；D06、D07 关闭；冻结核对时 RecommendationsPage.tsx 按 W6.2 片段比对。
   - W12.1：验收标准是 18/18；seed `.sha256` 与文件一致；D01 关闭。
   - W5.1+W5 页面：
     - 改写 W3 那 1 项断言为“允许新增可选字段，已有字段与必填项不变”。
     - 验收标准：W5 47/47、W3 186/186；页面对照 `screenshots/1440/10-interview-1440.png`，虚构数据有标注。
   - W16（以 W16.1 为准）：对照 `screenshots/1440/15-recs-1440.png` 和 `DEFECTS/W16.md` 8 条。
4. **W18.2（半天–1 天）**
   - 做：D08 修复，Assumptions 补写原文（`DEFECTS/W18.md:250-253`）。
   - 验收标准：
     - `W18_D08_EdgeWindow_AbsorbedIntoAdjacentViolationGroup` 由 KnownDefect 转为通过（改写断言，不删）。
     - 220 组随机对照仍一致；真实案例工休仍通过。
5. **W14.3（半天）**
   - 做：按 `DEFECTS/W14.md:278-283` 修。
   - 验收标准：窄谷用例差 ≤ 0.1 m；YANGZE 22 五个情景数值不变（误差 ≤ 0.01 m），否则先报告原因。
6. **W13 Unity 回放集成（本周开始，跨周）**
   - 做：
     - 原型 06（`screenshots/06-sim.png`，README 表第 6 行）的主仿真界面：动态海面与两船、时间轴（播放/倍速/拖动/事件标记）、HUD、实时 DCPA/TCPA 风险色、小地图、ECFC 弹卡、四种视角。
     - Unity 播放头与服务时间同步，数据用 W2 对齐后的时间轴和 W12 曲线。
     - 原型 08 右侧的“碰撞瞬间物理复盘”也归 W13（`DEFECTS/W12.md` 看图说明）。
   - 验收标准：
     - 纯逻辑部分有 dotnet 测试，且仍是 netstandard2.1、无 UnityEngine。
     - 拖动时间轴误差 < 0.1 s（`ARCHITECTURE.md` P6a 指标）。
     - Unity 场景部分写清操作步骤，**由 Mark 在 Unity 里验证**（`ROADMAP.md:33`）。
7. **之后**：W8（01 02）→ W9（03 04）→ W10（05）→ W11（07）→ W14 页面（12）→ W15 页面（14，先写 `systemic.schema.json`）→ W18 页面（13）→ W17（17）→ W19（16）→ W20 → W21；W4 接 align、W7 征求意见轮次可穿插。

---

## 9. 如何在单一 Codex 下工作

原来是多 bot 分工：DeepSeek / Claude Code 实现，Codex 验收，Gemini/Grok 架构裁定（`ROADMAP.md:3-8`）。实现方和验收方分开，靠冻结哈希防止“边测边改”。现在只有一个 Codex，建议保留这套隔离：

1. **实现会话**：只写实现和自测；完成后生成冻结清单（`sha256sum <files> > logs/<包>-impl-hashes-frozen.txt`），追加 ROADMAP「待测」，提交一个 commit。
2. **验收会话**：另开一个新会话，不带实现会话的上下文。
   - 只读规格（ROADMAP 包定义 + DEFECTS 裁定 + contracts + 原型截图），在 `tests_acceptance/<包>/` 写测试。
   - 开始和结束各跑一次 `sha256sum -c` 证明实现没动。
   - 写 `DEFECTS/<包>.md`，不改实现。
3. **裁定**：在 DEFECTS 文末写「架构裁定」，以合同和原型为准。拿不准的产品口径（真实数据边界、部署、等保等）记下来问 Mark，不要自拟。
4. 用 `git` 分支或独立 worktree 隔离实现和验收，减少共享文件互相覆盖。共享入口文件按片段核对。
5. 有独立参考实现的地方（RK4、分钟栅格暴力法、Python 暴力对照）继续用，数值结论要“独立算一遍对得上”才算过。

---

## 10. 未决事项

- **R7 部署阶段**（提议，**尚未写入 ROADMAP**；`HANDOFF.md` §8）：
  - 统一身份 LDAP/AD，角色 + 辖区权限；
  - 传输/存储加密与证据哈希；
  - PostgreSQL；
  - 加密案件包同步；
  - 本地托管模型；
  - 等保 2.0，可能有信创要求；
  - 容器化。
  - Mark 还没答复是否写入路线图；他需要向单位确认三件事：是否要求信创、等保级别、是否已有统一认证和 GPU 服务器。analysis 只读接口的角色权限已裁定并入 R7。
- **W16 GISIS**：对照表 `contracts/gisis-mapping.md` 已建，但 Table 5 本地等级（Serious/LessSerious）对应和部分字段仍「待核」（`REQUESTS.md` 22:20、22:25 段）。
- **`contracts/schemas/systemic.schema.json` 未写**（`HANDOFF.md` §6 末；`DEFECTS/W16.md:4`）。W16 报告的 W15 部分在此之前显示“缺数据”。
- **集成接口未做**：audit sink、custody sink、statement source（各包向统一审计/保管链/陈述来源写读的接口）。
- **脱敏网关**：服务有基础（`service/mcis_service/redaction/`，`contracts/CONTRACTS.md:95`），完整的字段级脱敏归 W17。
- **统一演示时间线**：以原型版 14:15–14:27 星屿港为准（`P6A_PLAN.md:16`），用重算值（`ROADMAP.md:68`），各页面/Unity 统一。
- W5 后续增强：中文数字时长（“两个小时”）和约数词邻接规则，本阶段维持现状（`DEFECTS/W5.md:69-75`）。
- W6 基线截图：20:57 原件已不可恢复，以 `tests_acceptance/W6/screenshots/runs/20261111-214028/` 为新基线（`DEFECTS/W6.md:134-140`）。

---

## 11. 交接时的仓库状态

- 分支 `main`，最新提交 `3e42024`；remote `github.com/mark2wen2023/MCIS`。
- 交接时未提交：`REQUESTS.md`、`ROADMAP.md`、`logs/w16.1-codex-1.log`（改）；`logs/w16.1-codex-last-1.md`、`logs/w5.1-impl-hashes-frozen.txt`（新）；以及本次新增/修改的 `docs/HANDOFF-STAGE1.md`、`AGENTS.md`、`HANDOFF.md`、`README.md`。
- `.gitignore` 排除依赖（node_modules、.venv）、构建产物（bin/obj/out、web/dist）、运行库（service/data、*.db）、密钥（.env、*.pem、*.key…）和本地代理目录（.codex/.agents/.aws）。克隆后要重建 `web/node_modules` 和 `service/.venv`。
- 备份目录（仓库外、不入库）：`/workspace/.w*-backup/`（DeepSeek）、`/workspace/w16-backup/`（Codex）。

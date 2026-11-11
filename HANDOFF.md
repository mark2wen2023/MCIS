> **已过时：最新的阶段性交接见 [docs/HANDOFF-STAGE1.md](docs/HANDOFF-STAGE1.md)（2026-11-11 22:30）。本文件仅作历史保留。**

# MCIS 交接说明（2026-11-11 快照，Asia/Shanghai）

给后续在 Codex（或其他环境）继续开发的接手文档。更细的状态以 `ROADMAP.md` 最新行和 `DEFECTS/*.md` 文末裁定为准；本文件是当时的汇总，不替代那些原始记录。

## 1. 项目简介

本仓库是 Mark Wen（WMU 硕士论文）的**海事事故调查仿真系统**（MCIS / MCIS-3D）：在 Unity 6 + URP 中做三维回放与推演，结合 Cesium、倾斜摄影、Enviro 3、Dynamic Water 2 与 AIS/VDR 数据，做成完整、接近游戏体验、高保真 UI 的调查工作台。原型里出现的每一项功能最终都要落地。

技术分层：

| 层 | 位置 | 说明 |
|---|---|---|
| 纯 C# 计算核心 | `unity/Assets/_Project/Scripts/{Core,Domain,Data,Simulation,…}` | C# 9、netstandard2.1，**不得引用 UnityEngine**。CPA/DCPA、COLREG、VDR/时间轴、笔录比对、系统分析、工休、What-if 等权威实现都在这里。 |
| mcis-core CLI | `tools/mcis-core/` | 源码 glob 引用上述 Scripts，不复制。stdin/stdout JSON；子命令目前有 `cpa`、`align`、`colreg`。 |
| 调查服务 | `service/` | FastAPI + SQLite，**只监听 127.0.0.1:8765**。案件存储、审计、脱敏、`.mcase`、调用 mcis-core。 |
| Web 工作台 | `web/` | Vite + React + TypeScript + ECharts。只通过服务的 HTTP 接口读写。 |
| Unity 三维 | `unity/` | 回放、HUD、与服务同步播放头。与工作台联调是 W13，尚未开始。 |
| 契约 | `contracts/` | 模块之间的唯一接口真相源：`openapi.yaml` + `schemas/*.json` + `CONTRACTS.md`。 |

## 2. 目录结构

```
maritime-sim-design/
  AGENTS.md, HANDOFF.md, ROADMAP.md, REQUESTS.md, P6A_PLAN.md
  ARCHITECTURE.md, BRIEF.md, README.md, thesis.txt
  contracts/          接口合同（OpenAPI + JSON Schema）
  DEFECTS/            各包缺陷单与架构裁定
  tests_acceptance/   独立验收测试（W1/W2/W3/W5/W6/W14/W15/W18…）
  service/            FastAPI 服务（mcis_service/；测试在 service/tests/）
  web/                Vite/React 工作台
  tools/mcis-core/    计算核心 CLI
  unity/              纯逻辑 Scripts + 各包 xUnit 工程 + Tools
  p2p5-src/           早期纯逻辑源码副本（部分 What-if 等曾同步）
  prototype/          高保真 HTML 原型（含 p6 各页）
  screenshots/        原型与实现截图（1920 与 1440/）
  reports/            公开事故报告结构化数据（海力5、YANGZE 22）
  samples/            虚构 Lily/Mary 演示报告与视频
  fonts/              报告用中文字体（Noto Sans SC）
  logs/               冻结哈希、自测/验收日志（请保留）
  diagrams/
```

运行时数据目录 `service/data/`（含 `mcis.db`）首次启动自动创建，已从版本库排除。分析页种子在 `service/mcis_service/analysis/data/`（JSON + sha256），**必须保留**。虚构演示种子在 `service/mcis_service/seed/`。

## 3. 如何构建和跑测试

工具：`~/.dotnet/dotnet`（或 PATH 中的 dotnet 8）；Python 3；Node.js / npm。服务和前端都只绑 `127.0.0.1`。

### 3.1 一键本地开发

```bash
./run_dev.sh              # 后端 127.0.0.1:8765 + Vite 127.0.0.1:5173
./run_dev.sh --preview    # 先 npm run build，再 vite preview :4173
```

环境变量：`MCIS_DATA_DIR`（默认 `service/data`，首次写入虚构 Lily/Mary 演示案）、`MCIS_PORT`（默认 8765）、`MCIS_API`、`MCIS_CORE`（默认 `tools/mcis-core/mcis-core.sh`）、`MCIS_SEED_DEMO`。

单独启动服务：

```bash
cd service
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m mcis_service    # host 写死 127.0.0.1
```

### 3.2 纯 C# 核心 / mcis-core

```bash
export PATH="$HOME/.dotnet:$PATH"
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1

# 各包自测（在对应目录）
~/.dotnet/dotnet test unity/Tests_W1_Colreg/Mcis.W1.Colreg.Tests.csproj
~/.dotnet/dotnet test unity/Tests_W2_Vdr/Tests_W2_Vdr.csproj
~/.dotnet/dotnet test unity/Tests_W3_Inv/Tests/W3.Inv.Tests.csproj
~/.dotnet/dotnet test unity/Tests_W5_Interview/Tests/W5.Interview.Tests.csproj
~/.dotnet/dotnet test unity/Tests_W14_WhatIf/Tests_W14_WhatIf.csproj
~/.dotnet/dotnet test unity/Tests_W15_Sys/Tests/W15.Sys.Tests.csproj
~/.dotnet/dotnet test unity/Tests_W18_HF/Tests/W18.HF.Tests.csproj
~/.dotnet/dotnet test unity/DotnetTests/Tests/Mcis.Pure.Tests.csproj
~/.dotnet/dotnet test unity/DotnetTests2/Tests/Mcis.Pure.Tests.csproj

# 独立验收
~/.dotnet/dotnet test tests_acceptance/W1/W1.Acceptance.csproj
# 其余包同理：tests_acceptance/W2、W3、W5、W14、W15、W18
# 真实案例参考（不计入通过率的包，按该包说明）：tests_acceptance/W1_realref

# CLI（首次或源码变更会自动 Release 构建到 tools/mcis-core/out/，该目录不入库）
echo '<json>' | ./tools/mcis-core/mcis-core.sh cpa     # 或 align / colreg
```

LibCheck（确认无 UnityEngine、目标 netstandard2.1）：`unity/Tests_W2_Vdr/LibCheck/`、`unity/Tests_W14_WhatIf/LibCheck/`。

### 3.3 服务测试

必须用 `service/.venv`，不要用仓库外的其他 venv。

```bash
cd service
.venv/bin/pytest                  # 全量
.venv/bin/pytest tests/test_colreg_w61.py tests/test_analysis_w12.py
```

已知：若 `openapi.yaml` 里已有 W16 `/reports`、`/gisis` 等路径而后端尚未完全实现，`test_openapi_yaml_matches_routes` 可能失败。这是合同与实现时序问题，不要用改合同的方式掩盖，除非有裁定。

### 3.4 Web 测试

```bash
cd web
npm install --no-audit --no-fund
npx tsc -b --force
npm test                 # COLREG 页 + W6.1
npm run test:w5          # 询问比对页
npm run test:w16         # 报告页
bash tests/run-analysis-w12.sh
npm run lint             # oxlint
```

`web/tests/.tmp-*.cjs` 是 esbuild 临时产物，已忽略，不要提交。

## 4. 开发流程

不可跳步：

1. 实现并自测通过。
2. 在 `ROADMAP.md` 状态表追加一行「待测」，**必须附冻结哈希**（被测文件清单 + sha256）。冻结期内不要改这些文件；改其他已验收包的冻结文件须先在 `REQUESTS.md` 登记。
3. 独立验收：测试放 `tests_acceptance/<包号>/`，缺陷写入 `DEFECTS/<包号>.md`，失败项标 KnownDefect。验收方不改实现代码。
4. 架构裁定后返工，再复测，直到清零或裁定延期。
5. **断言与裁定冲突时改写断言，不得删除用例。**
6. 标「已验收」后，才推进依赖它的下游包。

其它约束：

- 不 git push（除非仓库主人明确要求并亲自/授权推送）。
- 不打印、不外发任何密钥；不把 `.env` 或密钥文件提交进库。
- 不碰 `/workspace/yuehai-*`。
- 服务只监听 `127.0.0.1`。
- 阈值比较在 Domain 层用 double、容差 `1e-6`；边界用例用 ±1e-7，明显越界用 ≥1e-5。
- CLI 领域错误可用信封错误码，进程退出码 4。
- 冻结清单若走被测路径，须包含 `Domain/Evidence` 和 `tools/mcis-core`。mcis-core 基线哈希见 `logs/mcis-core-hashes-2106.txt`。
- 新样式写入独立文件（如 `web/src/styles/<pkg>.css`）再由入口引入；不要把共享 `styles.css` 放进单包冻结清单。

## 5. 真实数据口径

Mark 于 2026-11-11 20:20 确认（原文大意）：上传的事故报告都是公开资料，其中的真实数据和信息可以直接使用。

- 可用 `reports/` 下已上传的公开报告（目前主要是海力5、YANGZE 22），基准见 `reports/REAL_CASES.md`。
- 使用时必须标注来源，并标明每个数值是【直接】、【推算】还是【估计】。
- Lily / Mary（星屿港，约 14:15–14:27）演示案是**虚构**，必须标注「虚构」或「示例数据（虚构）」，不得写成真实事故。
- YANGZE 22 的规范 `caseId` 以 `reports/yangze22/case.json` 为准：`CJK-2024-1230-YangZe22-VegaDream`。不要用占位符 `CASE-REAL-YANGZE22`。

## 6. 各包当前状态（以 ROADMAP / DEFECTS 最新为准，本快照约 21:50）

仓库在交接时仍可能有其他实现/验收任务在写入，下表以当时文件为准，接手后请再读一遍 `ROADMAP.md` 文末。

| 包 | 状态 | 说明 |
|---|---|---|
| P0 平台骨架 | 已验收 | contracts、service 骨架、web 骨架、mcis-core cpa；证据中心与建议看板已接后端 |
| W1 / W1.1 COLREG | 已验收 | 规则引擎已接入 mcis-core `colreg` 与服务 evaluate |
| W2 / W2.1 / W2.2 / W2.3 VDR 与时间轴 | 已验收 | 系列结案；mcis-core `align` 已接入 |
| W3 / W3.1 / W3.2 笔录 / 建议 / 保管链 | 已验收 | 系列结案。`batchId` 作合同可选扩展、Submit 审计失败与 Confirm/Dismiss 对齐，随 W5.1 完成 |
| W4 证据中心页 | 页面主体已由 P0 完成 | 剩余：接通 W2 align |
| W5 询问比对核心 | **有条件通过**（45/47） | 纯 C# 核心已过。D01 陈述版本、D02 Resubmit→W5.1 |
| W5 页面 + W5.1 | **进行中** | service + web（原型页 10）；本快照时 `web/src/interview/`、`service/mcis_service/interview_compare/` 已有文件 |
| W6 / W6.1 避碰规则页 | W6.1 **有条件通过**（112/114） | D01–D05 已关。D06/D07 等见 W6.2 |
| W6.2 | **进行中 / 待做** | evaluate 返回 `runId`；扩展路由入 schema、`PENDING_CONTRACT=False`；PATCH 旧字段名标记废弃后删除；EvidencePage/RecommendationsPage 改读 `__MCIS_API__`；建议 1440 下判定表上移到首屏；W12 的 analysis 路由一并 `include_in_schema=True` |
| W7 安全建议看板 | 页面主体已由 P0 完成 | UpdateDraft 已在 W3.1 落地 |
| W8 大厅 + 案件管理 | 未开始 | `.mcase` 导入导出、完整性校验（原型 01/02） |
| W9 船舶/环境参数 | 未开始 | 原型 03/04 |
| W10 航迹编辑 | 未开始 | AIS 导入、清洗、手绘；原型 05 |
| W11 ECFC 编辑器 | 未开始（曾暂停） | 仅建空目录 `Scripts/Domain/EcfcEditor`、`unity/Tests_W11_Ecfc/Tests`，未写实现 |
| W12 分析页 | **待测** | 冻结 `logs/w12-impl-hashes-frozen.txt`（32 项）。独立验收进行中或待做。裁定见 `DEFECTS/W12.md`：两只读接口入合同；YANGZE 22 caseId 见上；Layout.tsx 补丁保留；航向当作对地航向须标【推算】 |
| W13 Unity 回放集成 | 未开始 | 主仿真界面、HUD、与服务时间同步；需在 Unity 里验证 |
| W14 / W14.1 / W14.2 What-if | 已验收 | 默认案例数字可采信。遗留 **W14.3**：D06 粗扫 0.5 s 漏检窄谷，改用积分步长扫描 |
| W15 / W15.1 / W15.2 系统分析 | 已验收 | 系列结案（Bow-tie / AcciMap / STAMP） |
| W16 报告生成 | **进行中** | IMO/MAIB/中国海事模板、中英双语、GISIS、PDF/DOCX、证据引用、Draft+审计、以及 W6 章节草稿后端。本快照时 `service/mcis_service/reports/` 与 `web/src/reports/` 已有代码，尚未在 ROADMAP 标待测 |
| W17 权限与脱敏 | 未开始 | 权限矩阵、字段级脱敏、访问审计 |
| W18 / W18.1 人为因素 / 工休 | W18.1 **有条件通过**（94/95） | 220 组随机排班对照一致。遗留 **W18.2**：D08 被记录首尾截断的休息段窗口不得从报告消失 |
| W19 知识库 | 未开始 | 相似案例检索等 |
| W20 智能体抽取 | 未开始 | 报告抽取 + 人工确认队列（本地/国产模型） |
| W21 集成发布 | 未开始 | Unity↔工作台联调、Windows 打包、演示数据统一、手册 |

`contracts/schemas/systemic.schema.json` 计划中但本快照时尚不存在，若接手系统分析页/合同，需补。

## 7. 未关闭缺陷与下一步（优先）

按当时演示优先顺序，建议：

1. **W12 验收**：按冻结哈希复核；独立重算三案 CPA 曲线；对照 W14.2 数字；篡改种子须返回 `analysis_seed_tampered`；截图对照原型 08。通过后在 ROADMAP 记结论。
2. **W16 报告生成**：做完自测后标待测并附冻结哈希，再独立验收。YANGZE 22 不要用错误 caseId。
3. **W6.2**：见上表及 `DEFECTS/W6.md` 21:43 裁定。
4. **W5 页面 + W5.1**：先改 contracts，再实现 D01（比对结果带 `statementVersion`，版本变化后旧结论标 stale）和 D02（仅从 `CrossCheckState.Dismissed` Resubmit，旧条目标 `Superseded` 并写审计）；顺带完成 W3 遗留的 Submit 审计失败返回 `crosscheck_audit_failed`、`batchId` 可选扩展键。验收方改写 KnownDefect 断言，不删除。
5. **W18.2（D08，必修）**：被记录边界截断的休息段所涉窗口，无论是否与确定违规组重叠，都必须在报告中可见（单独 InsufficientData，或在违规组上标注「含截断段」）。Assumptions 按 `DEFECTS/W18.md` 21:49 补写。
6. **W14.3（D06）**：粗扫改用仿真积分步长；在局部极小和转首率超阈值时段加密；构造 0.2 s 窄谷，与 0.01 s 暴力扫描相差不超过 0.1 m。见 `DEFECTS/W14.md` 21:12。
7. **W13** Unity 回放集成，以及其余未开始包（W8–W11、W9/W10、W17、W19–W21）。W4 接通 align 可穿插。

## 8. 提议中的 R7 部署阶段（尚未写入路线图）

Mark 要求「真实的部署可用」。架构建议：**内网联机版为正式产品**，另做**离线单机现场版**，同一代码库。R7 草案包括：

- 统一身份（LDAP/AD），角色 + 辖区权限
- 传输/存储加密与证据哈希
- PostgreSQL（替代或并列于开发用 SQLite）
- 加密案件包同步
- 本地托管模型
- 等保 2.0 合规；可能的信创要求
- 容器化部署

**尚未得到 Mark 书面确认是否写入 ROADMAP。** 组织侧待确认：是否要求信创、等保级别、是否已有统一认证和 GPU 服务器。只读分析接口的角色权限已裁定并入 R7，不记为 W12 缺陷。

## 9. 给 Codex 的接手建议：先读这些文件

按这个顺序读，再动手改代码：

1. 本文件 `HANDOFF.md` 与根目录 `AGENTS.md`
2. `ROADMAP.md`（流程 + 文末最新状态行）
3. `contracts/CONTRACTS.md`、`contracts/openapi.yaml`、`contracts/schemas/`
4. `P6A_PLAN.md`（通用规则与真实报告口径）、`REQUESTS.md`（未入合同的提案）
5. 与当前任务对应的 `DEFECTS/<包>.md` 文末裁定（不要只读摘要）
6. `reports/REAL_CASES.md` 以及将用到的 `reports/haili5/`、`reports/yangze22/`
7. 需要改 UI 时对照 `prototype/` 与 `screenshots/`（含 `screenshots/1440/`）
8. 架构细节查 `ARCHITECTURE.md`；启动方式看 `run_dev.sh`、`web/src/config.ts`、`service/mcis_service/config.py`

动手前先对将修改的路径做一次哈希或 `git status`，避免覆盖其他任务尚未提交的冻结文件。标待测时写出完整冻结清单。

## 补充（2026-11-11 22:01）
- W12 分析页：有条件通过（17/18，独立重算偏差 0），待 W12.1 补【推算】标注。详见 DEFECTS/W12.md。
- 共享入口文件（web/src/main.tsx、web/src/routes.ts、web/src/styles.css）不进单包冻结清单。

## 补充（2026-11-11 22:10）
- W6.2（DeepSeek）与 W16 报告生成（Codex）均已交付待验收，裁定分别见 DEFECTS/W6.md、DEFECTS/W16.md 22:10。下一步：按裁定改写 W6 旧用例后验收 W6.2；验收 W16；W12.1；W5 页面+W5.1；W18.2；W13 Unity 回放集成。

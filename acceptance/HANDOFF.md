# W12 正式分析接入交接（一页，可执行）

适用范围：把已核隔离结果交给后续正式接线，而不是再做一轮隔离测试。本文只记录源码定位与既有浏览器回执。不改产品、CI、契约、写权限，不发明新字段或假实现，不重跑旧套件，不做真实案，不合并、不部署。W21 暂停，本文只写如何识别旧派生版本，不实施 W21。

保护（标签选择、加载中清空、迟到响应不覆盖）位于隔离装配，**不认作正式产品**。此项不等于正式同案换版或 W12 整包。

查阅日期：2026-11-27（Asia/Shanghai）。源码以注明的 Git SHA 为准。

---

## 1. 固定 SHA

**主线（已查，不是猜测）**：远端默认分支 `origin/HEAD` → `refs/heads/main`，当前 `94d5e38c926fda232bb987b60fa9145e4bcf01a7`（2026-11-15 07:03:42 +0800，Merge PR #91）。本地检出的过期 `main` 不得当作主线。

| 角色 | 完整 SHA | 说明 |
| --- | --- | --- |
| 主线默认分支 | `94d5e38c926fda232bb987b60fa9145e4bcf01a7` | `origin/main` |
| 本单底版 / 隔离同案配对候选 | `f1413042624dedf8e08c1b516818e8c48c677480` | `candidate/w12-same-case-pair-select` |
| 上项证据（孤立） | `c5c73d0c55ed5b9b558e17b7a1306671aca8e78d` | `evidence/w12-same-case-pair-select-grokbot-f141304` |
| 策略拒绝候选 | `688a7bb0eb16b29bb295d13376ab56f4cc7fd10b` | `candidate/w12-request-time-policy-deny` |
| 上项证据 | `98c1860435f0736cf4335817d5743dae1573dec6` | `evidence/w12-request-time-policy-deny-grokbot-688a7bb` |
| 请求时读取候选 | `f7b1f11e719f4ebba0a3a1f6146fadbe3ba8d346` | `candidate/w12-request-time-read` |
| 上项证据 | `07ff21954f1dbd484170c81b818bdfec9ab182d9` | `evidence/w12-request-time-read-grokbot-f7b1f11` |
| 说明用词修正 | `7345c1eb5ee6fb76558d88ff6d75172145b53ea2` | `candidate/w12-registered-json-gap-caption` |
| 上项证据 | `4bc7c2a7ed2e959c05e6758726f24794800a320b` | `evidence/w12-registered-json-gap-caption-grokbot-7345c1e` |
| 已登记缺口 JSON | `e80a49aba61336f8db7b1337b6a555de5c735857` | `candidate/w12-registered-json-gap` |
| 上项证据 | `52734ac9d0002f893ee83cb30bab362a0696a5c0` | `evidence/w12-registered-json-gap-grokbot-e80a49a` |
| 可见性（更早已核） | `c150548c16516f5ad7319e3a00213e5fbe448497` | `candidate/w12-registered-visibility` |
| 冻结读取白名单 | `db90fdf73de7bd26ba75819f0102fc03d0789faf` | `_load_registered_pair` 所在生产针，仅隔离物化，未并入正式路由 |
| 同案独立登记方法 | `afc72a1180ae345556a85fb63a4020a476893d14` | 临时库两份原件，不是正式换版 |
| 分析快照针 | `03a8e7867fedbaaabbf8dd12fc9041d6a1a74cd5` | 历史接线核查用针 |
| 锁定合成夹具 | `2048c60fd6650c6f2c99a76a16be463a3895655d` | vessel-A `a8f9109a…28bb1c`，vessel-B `07e043fc…59ca` |

`service/mcis_service/analysis/router.py`、`tracks_import/*`、`track_history/*`、`reports/service.py`、`reports/sources.py`、`contracts/W10.2-track-input.md`、`ReplayCommand.cs` 在主线 `94d5e38` 与底版 `f141304` **字节相同**。差异只在候选链上的 `web/src/analysis/*` 与 `AnalysisPage.tsx`（未进主线）。

---

## 2. 最小正式分析接线

**目标**：正式 `GET /api/v1/analysis/cases` 与 `GET /api/v1/cases/{case_id}/analysis` 接到已验的「请求内读取已登记原件并实算」能力。本单不实施。

### 已有证据（隔离，不是正式产品）

- 装配入口是隔离 HTTP `/assembly/api/view?pair=pair-a|pair-b`，使用冻结 `_load_registered_pair` 与真实 `mcis-core`，不是正式 `/analysis`。源码：`tests_acceptance/w12-same-case-pair-select/`（`f141304`）。
- 官方沙箱 Chrome，2026-11-27 20:04:03–20:04:17 CST（Asia/Shanghai），`127.0.0.1:18785`，`chromium_sandbox=True`，退出 0。先显示配对 A，再选 B，加载中不保留 A；B 用新登记原件实算 T+120 `currentDistanceNm=1.226641`（Warning），与 A 的 `1.070062`（Danger）可对；切回 A 后，迟到的 B 完整 200 已抵达但未覆盖 A。回执：证据 `c5c73d0`，`official/late-b-ignored.json`、`host-request-log.json`、`official/shots/`；评论 [7217832413](https://github.com/mark2wen2023/MCIS/issues/106#issuecomment-7217832413)。Dot 复核 [7218181518](https://github.com/mark2wen2023/MCIS/issues/106#issuecomment-7218181518)。
- 请求时读取与策略拒绝（`f7b1f11` / `688a7bb`）证明允许与拒绝两条上下文在同一隔离 GET 内都调用冻结读取入口；不重跑。

### 确切阻塞（首个断点；已用当前源码复核，结论不过时）

文件：`service/mcis_service/analysis/router.py`

- 主线 `94d5e38`、底版 `f141304`、历史针 `03a8e786` 三针字节相同。
- SHA-256：`b3e91f7606b20da2c4ec1f07de396df0d041603dfbea694431a963f6e41bb4be`
- 位置：`load_seed` / `_meta` / `list_analysis_cases` / `get_analysis`（36–78 行）

现状：正式分析只读离线 `data/w12-analysis-seed.json`，按旁注自检后输出 `seedSha256`；运行时不调用 mcis-core、不读登记航迹、不调用 CPA。因此不能把隔离装配的请求时读取直接称作正式 `/analysis` 已接通。历史「约 36–78 行没有同案换版 API」的判断，对当前主线仍然成立，无需更正断点位置。

### 相关但非首个的阻塞（不要跳过首个断点去改这些）

1. **正式航迹写入不能保存同船第二版**。`tracks_import/parser.py` 第 158 行 `TRACK_EXISTS`（「该船已有航迹，本切片不覆盖、不追加」）；`tracks_import/router.py` 第 243–244 行提交时 409。合同 `contracts/W10.2-track-input.md` 第 40 行（SHA-256 `51d2435d86553cdb869ded3642f20cfa5b515d76b869b6f06f7de51a220bc9de`）：本切片为「首次保存且不支持后续编辑」。即使分析改接身份，一案两版本仍无法经现有 commit 持久化。不要放宽该拒绝。
2. **已有只读身份 API，分析未消费**。`GET /api/v1/cases/{case_id}/track-imports?vesselId=`（`tracks_import/router.py` 296–320 行）与 `GET .../track-imports/{digest}`（323–330 行）可返回 `caseId` / `vesselId` / `previewDigest` / `sourceSha256`。归档 `GET .../archive-history/track-imports` 是 `archive-only` 且 `identityMode: unverified-self-reported`，不是当前活跃版。
3. **主线前端没有「按登记身份失效」的钩子**。`useAnalysisSnapshot.ts` 在 `03a8e786` 与候选 `f141304` 存在且字节相同（SHA-256 `ac9da6f6bc6fa8d01ff24aa3fc4247a6269a1bfe1756df109e607eb4e0a53910`），作用域只含 `caseId`+角色+操作者，只核对 `seedSha256`，不读 `previewDigest` / `sourceSha256`。该文件在主线 `94d5e38` **不存在**。主线 `AnalysisPage.tsx`（SHA-256 `17ef299460d1f81d71eedeb0be17edf3f3b083e5f77983f31d66bff9d5d5c3dd`）直接 `useLoad` 打正式 `/analysis`。候选页上的「只代表本次读取，未确认登记轨迹实时版本」不是主线行为，也不是版本确认。
4. **隔离标签不是正式契约字段**。`pair-a` / `pair-b` 仅出现在隔离主机；不要把它们写进正式 API 或存储。

### 后续最小接线（授权后再做；本文不实现）

1. 正式分析读路径改为先取本案计算所需各船的当前本地回执（复用已有 `list_inputs` / `load_receipt`）。缺任一已验证来源则不返回分析结果，不得回退到种子文件或旧响应。
2. 响应元数据携带与回执相同的已有身份字段：每船 `caseId`、`vesselId`、`previewDigest`、`sourceSha256`。禁止把 `seedSha256` 称为登记版本。不发明新字段。
3. 计算复用现有 `track_points` / `state_at` 与 CPA/核心调用，输入必须是上述身份对应的点。
4. 前端作用域纳入分析响应中的登记身份；身份变化时先清空旧快照。主线需另议是否引入钩子，不得把未合并的候选页当作已上线行为。
5. 同船换版写入仍是单独合同（W10.2 已推迟），不在分析接线里放宽 `TRACK_EXISTS`。

---

## 3. 输入版本由谁确认

### 已有证据

- **正式航迹输入**：由调查组操作者在预览后明确确认（`confirmed: true` + 预览得到的 `previewDigest`），服务器重算解析与绑定摘要，绑定原 bytes；禁止信任客户端发回的点列表。依据：`contracts/W10.2-track-input.md` 第 3、26–27、40 条；`tracks_import/parser.py` 第 69、76–77、158–160 行；`tracks_import/router.py` 第 218–259 行。身份键是服务器计算的 `previewDigest`，不是整数版本号。
- **隔离装配**：测试主机预先用冻结 `preview_input` / `commit_input` 登记两套合成配对，pin 留在服务端；浏览器只选已确认标签，不提交 pin。这是测试角色上下文，**不是**正式身份认证，也不是产品上的版本确认。回执见第 2 节 Chrome 原件与 `official/pin-rejected.json`（带 `sourceSha256` 的选择返回 400，`PIN_NOT_ACCEPTED`）。

### 确切阻塞 / 缺失

- **正式分析路径没有「确认当前登记航迹版本」的产品步骤**。正式 `/analysis` 只验证离线种子哈希（`load_seed` 36–46 行）。没有操作者对 `previewDigest` 集合的确认，也没有分析响应里的登记身份可供确认。找不到现成机制，不发明确认字段。
- 因此：航迹「谁确认」仅适用于首次导入那一次；分析页当前无人确认所用原件是否仍是那次导入。

---

## 4. 旧报告如何仍指回旧证据

### 已有证据

- 正式报告每次生成或再生成都**另存**同一 `familyId` 下的新 `reportId` / `version`，旧报告文档（章节、复核）不覆盖。`reports/service.py` `create_report` 第 98–129 行；`reports/router.py` `POST .../reports/{report_id}:generate` 第 101–105 行；合同 `openapi.yaml` 该操作摘要：「另存 familyId 相同的新版本，旧章节与复核不覆盖」。旧报告行本身可按 `reportId` 再读。
- 生成时把句子正文写入该份报告文档；引用通过 `_citation` 记录 `kind=evidence` 与 `id=evidenceId`（`reports/sources.py` 第 157–161、201–215 行）。证据台账项带有登记时的 `sha256`（`evidence/service.py` `REGISTER_FIELDS`）。
- 隔离侧：`afc72a1` 证明两份同案独立登记原件各有 pin，按旧 pin 重读字节与字段不变、不取 latest。这只覆盖冻结登记读取，不是报告持久引用。

### 确切阻塞 / 缺失

- 报告引用**不包含** `sourceSha256` 或 `previewDigest`。打开旧报告再跟随 `evidenceId` 去读库时，`evidence/service.py` `derive`（110–117 行）若存在 `Change` 保管事件，会把 `currentSha256` 改成新值。因此不能仅凭「另存了一版报告」断言引用永远钉在生成当时的原件字节。
- 主线 `94d5e38` 与底版 `f141304` **都没有** `reports/sentence_binding.py`。该文件只出现在未并入默认分支的提交（例如 `73a1fa7`）。`afc72a1` 对那份未合并报告候选的判断（轨迹 pin 不能转成音频句绑定，没有可信轨迹 `BindingReadScope`）在当前主线上应表述为：**缺失**轨迹引用类型及与报告/证据授权同读的产品调用点，而不是假定主线仍有该文件第 172–210 行。
- 正式航迹当前不能保存同船第二版（见第 2 节 `TRACK_EXISTS`），所以主线还没有「旧报告钉死旧航迹版、新报告钉死新航迹版」的端到端对象可验收。不要把隔离配对标签写进报告合同。

---

## 5. 给 W13 / W21 的旧派生版本如何识别

### 已有证据

- W13.1 本地回放命令与状态快照按 **`caseId`（及可选 `vesselId`、仿真时刻）** 隔离，没有登记航迹摘要字段。`unity/Assets/_Project/Scripts/Presentation/ReplaySync/ReplayCommand.cs`（SHA-256 `a0969b92bd9606262a392edce549776bb625eeb82413434b20ae932db58b1b26`）字段为 `Seq`、`CaseId`、`Type`、`SimTimeSec`、`Rate`、`VesselId`、`Reason`、`CreatedUtc`、`IssuedBy`；`ReplayStateSnapshot` 为 `CaseId`、时间、播放、速率。`tests_acceptance/W13/ReplayAcceptanceTests.cs` 用 `CASE_MISMATCH` 拒绝不同案号，不比较 `previewDigest` / `sourceSha256` / `seedSha256`。
- 规则引擎派生有自己的版本：COLREG 运行「另存为新版本（Draft）并设为当前；旧版本与复核不覆盖」（`colreg/router.py` 约 277–342 行，`runId` / `version` / `activeRunId`）。这是核查结果版本，**不是**航迹原件版本，不能用来识别「哪一套已登记原件」。

### 确切阻塞 / 缺失

- **找不到**把 `previewDigest`、`sourceSha256` 或分析所用原件身份传入 W13 回放命令/快照的现成机制。仅凭 `caseId` 无法区分同案两套已登记原件（隔离里已证明两套摘要与同刻核心值不同）。不发明新字段。
- W21（Unity ↔ 工作台联调、打包、演示数据统一）在路线图中为集成发布项，**当前暂停**。在现有 ReplaySync / 工作台协议源码中未找到「旧派生航迹版本」标识。本单不实施 W21，也不把隔离装配结果称为 W13/W21 已接通。

---

## 6. 执行时不要做的事

- 不要把本交接或任何子项写成 W12 整包通过，或写成正式同案换版已接通。
- 不要改正式认证、路由、契约、存储、写权限或核心；不要放宽 `TRACK_EXISTS`。
- 不要追加同类隔离演示，不要重跑权限、数学、缺口或配对套件。
- 不要把 `pair-a` / `pair-b`、隔离角色头或测试延迟参数产品化。
- 不要调用或部署 W21，不要改 mcis-3d。

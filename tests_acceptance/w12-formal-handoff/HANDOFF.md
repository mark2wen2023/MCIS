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

---

## 7. 本单核查：最小正式分析读取（停止编码）

核查日期：2026-11-27（Asia/Shanghai）。底版 `51370ffb67bd9e28188068f2014aa234a2428ef0`，主线 `94d5e38c926fda232bb987b60fa9145e4bcf01a7`。本单目标是在隔离候选上，经**实际分析页的正式请求路径**验证「一案一对、首次已登记合成航迹」的最小正式分析读取：由已登记回执与既有授权链解析两份服务端身份，真实计算；无回执／不同步／无双船同刻不给数，不回退演示，输入身份可核对。不做持久换版，不绕过 `TRACK_EXISTS`，不改 OpenAPI，不造新字段，不借演示 key，不填假的 seed/self-check，不用零代缺点。

结论：**现有已授权正式分析返回约定容不下这一步。已停止编码。浏览器回执未验。** 候选不是正式验收。

### 首个断点

文件：`contracts/openapi.yaml`（主线 `94d5e38` 与底版 `51370ff` 字节相同）

- SHA-256：`6e8a22e81c2959a20c2c66af09c458c81af6b6083e17985109fe2fa4d99f7236`
- 位置：第 644–706 行（W12 分析页合同：`AnalysisMeta`、`AnalysisCaseListItem`、`AnalysisCaseList`、`AnalysisCurvePoint`），并由第 819–853 行 `AnalysisCase`、第 2607–2648 行正式路径绑定到实际分析页请求。

既有返回约定与本单要求的冲突（逐项，均已对源码核对）：

1. **列表 key 只有三个既有样例。** `AnalysisCaseListItem.key` 为枚举 `lily-mary` / `haili5` / `yangze22`（683 行）。`GET /api/v1/analysis/cases`（2607–2624 行，摘要写明「只读种子」）返回的清单必须是该枚举。首次已登记的合成航迹不能作为第四个 key 出现在正式清单里。借用三个演示 key 被明确禁止。
2. **列表和详情都要求种子元数据。** `AnalysisMeta`（664–677 行）必填 `seedSha256`、`seedVerified`、`generatedAt`、`generator`、`coreVersion`、`coreDll`、`w14Export`、`w14Frozen`、`crossCheck`、`disclaimer`。`AnalysisCaseList` 通过 `allOf` 并入该元数据（688–694 行）；`AnalysisCase.meta` 必填且引用同一 schema（821、853 行）。正式详情路径 `GET /api/v1/cases/{caseId}/analysis`（2625–2648 行）写明 path 可以是规范 caseId 或短 key，**案例不在种子中时 404** `analysis_case_not_found`。已登记回执身份（`previewDigest` / `sourceSha256`）不是这些必填字段。把离线种子哈希或 `seedVerified=true` 填到登记读取结果上，属于假的 seed/self-check，被明确禁止。
3. **`AnalysisCurvePoint` 要求非空距离与风险等级。** 第 695–704 行：必填 `t`、`clock`、`distanceNm`、`dcpaNm`、`tcpaMin`、`riskLevel`；其中 `distanceNm` 类型为 `number`（不可空），`riskLevel` 为字符串枚举 `Safe` / `Warning` / `Danger`（不可空）。`dcpaNm` / `tcpaMin` 已允许 null，但距离与风险不允许。因此「无回执／不同步／没有双船同刻点就不给指标」无法写入 `baseline.series`：既不能空着距离，也不能用 0 代缺点（被明确禁止）。W10.2 首次登记 CSV 没有显式缺口字段，无同刻只能称「无观测」，不能改称「原件声明缺口」；即便如此，合同仍要求每个曲线点有非空距离和风险等级。
4. **原 `AnalysisView.tsx` 把种子摘要写成自检。** 主线 `94d5e38` 文件 SHA-256 `99aafc4d2ec59ef7e02724b2a890c20fa581f3b5f33dcde68e063a77a085348c`，第 151 行：`种子 sha256 {shortSha(data.meta.seedSha256)} · {data.meta.seedVerified ? '已自检' : '未自检'}`。正式分析页走上述两个 GET，把响应里的种子元数据展示为自检。不改合同、不改该展示的前提下，登记读取结果也会被写成种子自检。

相关但非本单首个断点（不要跳过合同去改实现）：

- 实现仍只读离线种子：`service/mcis_service/analysis/router.py` 第 36–78 行，三针字节相同（见第 2 节）。这是同一合同的实现，不是另一条已授权的正式分析读取入口。
- `GET /api/v1/cases/{case_id}/track-imports` 等只读回执入口仍然存在，且可解析服务端身份；但它们不是实际分析页的正式请求路径，也不能绕过上述返回约定把「有身份的真实计算、无同刻不给数」送进 `/analysis`。
- `state_at` 仍不可直接作为缺口安全采样。因已停在返回约定，本单未实现点级取样，也未跑浏览器。
- 正式 `TRACK_EXISTS`、演示种子路径须保留：本单未改写入、认证、持久层、核心或合同。

### 最小需审批项（批准前不编码）

若后续要继续「最小正式分析读取」，至少需要审批以下合同与展示变更；在此之前不写实现、不跑绿。不发明未经批准的字段。

1. **清单与详情允许非演示、已登记案例**：放宽或另定 `AnalysisCaseListItem.key`（及详情 path/404 语义），使首次已登记合成航迹不必借用 `lily-mary` / `haili5` / `yangze22`，也不必先写入离线种子文件。列表摘要不再只能是「只读种子」。
2. **分析响应的身份改为已登记回执，而不是种子自检**：`AnalysisMeta`（及页上「种子 sha256 / 已自检」文案）须能表达 `previewDigest` / `sourceSha256` 等既有回执字段，或允许在无种子时不返回 `seedSha256` / `seedVerified`。禁止用占位哈希或假 `seedVerified` 顶替。
3. **曲线点允许无指标**：`AnalysisCurvePoint.distanceNm` 与 `riskLevel` 须可空，或另有不改语义的缺口/无观测表示。没有双船同刻观测时不给数；W10.2 CSV 路径只称「无观测」。禁止用 0 或其他数值填洞。点级取样仍须先判显式缺口（仅已验合成 JSON）、有效覆盖与确有同刻，不得把 `state_at` 端点夹紧或插值当成实测。
4. **保留现有演示路径**：三个种子样例、种子旁注自检与现有 what-if 演示不得被这次登记读取替换或破坏。
5. **范围不变**：不绕过 `TRACK_EXISTS`，不做持久换版，不改认证策略、持久层或核心，不做历史报告、W21、真案或 4A。

在上述审批完成前，本隔离候选只更新交接文档，不改产品代码。官方沙箱 Chrome：**未验**。

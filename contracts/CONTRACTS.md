# MCIS 模块契约（contracts/）

> 版本 v1（2026-11-11）。本目录是四个模块之间**唯一**的接口真相源：JSON Schema（`schemas/`）+ HTTP 接口（`openapi.yaml`）+ 本说明。
> 演示数据（Lily / Mary、星屿港）全部为**虚构**，与任何真实事故无关。

## 1. 模块与数据流

| # | 模块 | 位置 | 角色 |
|---|------|------|------|
| ① | 纯 C# 计算核心 | `unity/Assets/_Project/Scripts/{Core,Domain}`（只读引用）+ `tools/mcis-core/`（CLI 外壳） | CPA/DCPA、COLREG 判定、时间对齐、保管链/审计格式的**权威实现** |
| ② | Unity 3D 推演 | `unity/` | 三维回放、SimTime 播放头；读 `.mcase`，通过本地 HTTP 与 ③ 同步 |
| ③ | Python 调查服务 | `service/`（FastAPI + SQLite，仅监听 127.0.0.1:8765） | 案件数据的存储与业务规则、审计、脱敏网关、`.mcase` 导入导出、智能体草稿队列 |
| ④ | Web 调查工作台 | `web/`（Vite + React + TS + ECharts） | 调查员界面，只经 ③ 的 HTTP 接口读写 |

```
            .mcase（ZIP + manifest.json + SHA-256）
   ② Unity  ───────────────────────────────►  ③ service  ◄──── HTTP/JSON ────  ④ web
      ▲  │        GET case/timeline/tracks          │  ▲
      │  └── PUT sim/state（播放头）────────────────►│  │ stdin/stdout JSON
      └──── GET sim/commands?afterSeq（seek 指令）───┘  ▼
                                                   ① mcis-core（dotnet CLI，复用同一份 C# 源码）
```

## 2. 生产者 / 消费者

| 契约（schemas/） | 生产者 | 消费者 | C# 对应类型 |
|---|---|---|---|
| `case` / `vessel` | ③（种子 / 导入）、② 写 case.json | ②③④ | `Mcis.Domain.Models.CaseDefinition` / `VesselDefinition`（case.json 键序与 `CaseJson` 一致） |
| `track-point` | ③（种子 / 导入 `derived/tracks/*.track.json`） | ②④、①cpa | `TrackPoint` |
| `evidence-item` | ③ | ④、②（evidence/index.json） | `Mcis.Domain.Evidence.EvidenceItem` + 推导字段（`EvidenceStatus`） |
| `custody-event` | ③（写 `audit/custody.jsonl`） | ④、② `CustodyLedger.Load` | `CustodyEvent`（**行格式逐字节一致**，见 §4） |
| `timeline-event` / `conflict` | ③（种子 / 智能体确认后写入） | ②④ | `Domain/Timeline`（W2，`TrackKind` 名称一致） |
| `interview`（含 statement、crossCheckResult） | ③ | ④、智能体（经脱敏） | `Domain/Interview`：`InterviewRecord` / `Statement` / `CrossCheckResult` + `CrossCheckEntry` 状态 |
| `colreg` | ①colreg（W1 交付前为种子） | ④②（时段着色） | `Domain/Colreg`（W1） |
| `recommendation` | ③ | ④ | `Domain/Recommendations.SafetyRecommendation` |
| `consultation-round` | ③ | ④ | `ConsultationRound` / `ConsultationReply` / `ConsultationComment` |
| `audit-event` | ③（每次写操作） | ④、② | `InvestigationAuditEntry`（7 个标准键）+ 扩展键 |
| `agent-draft` | 智能体（`AgentService` 角色） | 调查员人工确认 → ③ 写回目标实体 | —（ARCHITECTURE §15.5） |
| `access-policy` | ③（首席调查官可改） | ③ 脱敏网关、④ | — |
| `sim-state`（state / command） | ②（state）、④（command） | ④（state）、②（command） | — |
| `core-cpa` | ①mcis-core | ③ | `CpaCalculator` / `CpaResult` / `RiskThresholds` |

字段命名规则：camelCase、与 C# 属性名一一对应（`Id→id`、`DueUtc→dueUtc`、`ProgressPct→progressPct`）；时间一律 UTC ISO `yyyy-MM-ddTHH:mm:ssZ`（截断到秒，`AuditJson.FormatIso`）；SHA-256 小写十六进制；`SimTime` 秒 = `utc − case.caseEpochUtc`。标注“（只读）”的字段由服务推导，写入时忽略或拒绝。

## 3. Unity ↔ 服务（openapi.yaml 中 tag = `unity`）

| 用途 | 接口 |
|---|---|
| 取案件 | `GET /api/v1/cases/{caseId}`、`GET .../vessels`、`GET .../tracks?stepSec=&fromSec=&toSec=` |
| 取时间线 | `GET .../timeline?fromSec=&toSec=`（事件 + 冲突） |
| 推送当前 SimTime | `PUT .../sim/state` `{simTimeSec, playing, rate, source:"unity"}`（高频，内存态，不写审计） |
| 跳转到某时刻 | Web 发 `POST .../sim/seek {simTimeSec, reason}`（写审计）；Unity 轮询 `GET .../sim/commands?afterSeq=N` 取指令，执行后再 `PUT sim/state` 回报 |

约定：Unity 每 ≥200 ms 推一次 state；轮询周期 250–500 ms；`afterSeq` 用上次返回的 `lastSeq`。离线时 Unity 直接读 `.mcase`，联机只用于同步播放头。

## 4. 文件格式（与现有 C# 完全兼容）

### 4.1 `.mcase`
ZIP，根目录 `manifest.json`：`{packageFormat:"MCIS-MCASE", packageVersion:"1.0.0", caseId, createdAtUtc, lastModifiedAtUtc, generatorVersion, files:[{relativePath, role, sizeBytes, sha256}]}`。
`role` 按 `InferRole`：`case.json→CaseDefinition`，`raw/`、`evidence/→RawEvidence`，`audit/→Audit`，`exports/→Export`，`thumbnails/→Thumbnail`，其余 `Derived`。
完整性判定同 `IntegrityChecker`：**缺失或篡改即无效（导入 422 INTEGRITY_FAILED）；多余文件只报告**。审计链/保管链断裂 → 422 CHAIN_BROKEN；caseId 已存在 → 409 CASE_EXISTS。
服务导出的附加文件：`case.ext.json`、`vessels.json`、`derived/tracks/<vid>.track.json`、`evidence/index.json`、`analysis/{timeline,time-alignment,colreg}.json`、`testimony/IR-xx.json`、`recommendations.json`、`consultation/rounds.json`、`agents/drafts.json`、`access-policy.json`、`audit/{audit,custody,agent}.jsonl`。缺少 `evidence/index.json` 的 Unity 侧包，证据登记快照从 custody.jsonl 的 Register 行还原。

### 4.2 `audit/audit.jsonl`
每行扁平 JSON：先 7 个标准键 `utc, operator, action, category, command, before, after`（顺序固定），再扩展键（snake_case）`seq, role, entity_type, entity_id`，最后 `prev` = 上一行 UTF-8 字节的 SHA-256（首行 64 个 0）。字符串转义同 `AuditJson.Escape`（`\\ \" \n \r \t`，其余控制字符 `\u00xx`，非 ASCII 原样）。数据库层用 SQLite 触发器禁止 UPDATE/DELETE（append-only）。
业务动作名与 C# 写法一致：`safetyrec.create/transition/response/progress`、`consultation.open/reply/waive/decide/close`、`interview.crosscheck.batch_confirm`、`interview.contradiction.confirm/dismiss`、`custody.register/access/change/verify/review`。

### 4.3 `audit/custody.jsonl`
与 `CustodyEvent.ToJsonLine` **逐字节一致**（测试 `test_custody_jsonl_accepted_by_csharp_ledger` 用 `tools/mcis-compat` 编译 Unity 侧原样 C#，跑 `CustodyLedger.Load` 校验）：标准 7 键 → `seq, evidence_id, sha256, detail` → 可选 `result`（Verify：match/mismatch；Review：needs_review/cleared）→ Register 行另有 `title, source, extracted_by, extracted_utc, path`，非默认时 `case_id`、`confidentiality:"Restricted"` → `prev`。
“需复核”标记只能经 Review 事件设置/解除（`PATCH .../evidence/{id} {needsReview, reason}`，理由必填）；`EvidenceStatus` 推导：NeedsReview 优先，其次最近一次校验结果，Change 之后未重新校验为 Unverified。

## 5. Python → C# 核心：`mcis-core`

```
tools/mcis-core/mcis-core.sh <子命令>  < request.json  > response.json
```
- 构建：`~/.dotnet/dotnet build tools/mcis-core/McisCore.csproj`；csproj 以 glob 引用 `unity/Assets/_Project/Scripts/{Core/Primitives,Domain/Common,Domain/Models,Domain/Geo,Domain/Cpa}`，**不复制源码**。`mcis-core.sh` 在源码变化时自动重编到 `out/`，再以 `dotnet out/mcis-core.dll` 运行（apphost 找不到运行时，故用包装脚本）。
- 响应外壳：`{"ok":true,"command":"cpa","coreVersion":"mcis-core/0.1.0","result":{…}}`；失败 `{"ok":false,"command":…,"error":{"code","message"}}`。
- 退出码：0 成功；1 内部错误；2 未知子命令；3 `NOT_IMPLEMENTED`；4 请求错误（BAD_JSON / BAD_REQUEST）。服务把 `NOT_IMPLEMENTED` 映射为 HTTP 501，请求错误映射为 422。

| 子命令 | 状态 | 请求 → 结果（schema） |
|---|---|---|
| `version` | ✅ | → `{coreVersion, commands}` |
| `cpa` | ✅ | `core-cpa#/$defs/request`：`{pairs:[{pairId?, own, target, timeSec?}], origin?, thresholds?}`，船位 `eastNm/northNm` 或 `latDeg/lonDeg`（经 `GeoMath.Wgs84ToEnu` 转换）+ `speedKn/courseDeg` → `core-cpa#/$defs/result`（`CpaCalculator.CalculateByVector` + `EvaluateInstantRisk`） |
| `colreg` | ⏳ 返回 NOT_IMPLEMENTED | 待 W1 `Domain/Colreg` 稳定后接入；输出须符合 `colreg.schema.json`（bands + checks） |
| `align` | ⏳ 返回 NOT_IMPLEMENTED | 待 W2 `Domain/Timeline`（ClockOffsets / ConflictDetection）；输出 `conflict[]` + 时钟偏差 |
| `crosscheck` | 📝 计划 | 待 W3 `StatementCrossChecker`；输出 `interview#/$defs/crossCheckResult`，服务登记为 PendingConfirmation |

## 6. 业务规则（服务端强制，与 C# 一致）

- **安全建议**：状态 `Draft→Issued→Responded→{Implemented|NotAdopted|Closed}`，`Implemented/NotAdopted→Closed`；进入 Responded 只能 `POST .../responses`（= `RecordResponse`）；NotAdopted 必须写理由；`progressPct` 仅 Responded 可改（= `SetProgress`），进入 Implemented 自动 100；`verificationNote` 取最近一次进入 Implemented/Closed 的说明。看板四栏 = `KanbanColumn`：草拟=Draft、已发布=Issued、落实中=Responded、已关闭=Implemented/NotAdopted/Closed。内容字段修改是服务扩展，仅 Draft 可改。
- **征求意见**：上一轮关闭才能开新一轮；默认 30 天（MSC.255(84) 第 13 章）；一方只能回复或放弃一次；非 Adopted 的采纳决定须写反馈、每条只决定一次；关闭条件 = 各方均已回复/放弃，或已过期限。
- **询问比对**：所有比对结论登记后均为 `PendingConfirmation`，**须调查员确认才生效**（只有 Confirmed 计入矛盾数/进入分析）；一致项可批量确认（`crosscheck:confirm-consistent`），矛盾/无法核实逐条确认；驳回需写理由。
- **证据**：编号 `EV-NNN`、笔录 `IR-NN`；登记快照（含 `confidentiality`）不可改；Restricted 证据不对外部角色（ExternalExpert / InterestedState / AgentService / Public）列出。
- **脱敏网关**：请求头 `X-MCIS-Role`（LeadInvestigator / Investigator / ExternalExpert / InterestedState / AgentService / Public）与 `X-MCIS-Operator`（URL 编码）。按 `access-policy` 矩阵与字段规则 FR-01..05 处理；`GET interviews/{id}` 的响应头 `X-MCIS-Redaction` 列出生效规则；外部角色读取证词写 `testimony.read` 审计。智能体输入一律按 AgentService 脱敏（姓名替换为 `<ROLE_xx>`）。
- **智能体**：只登记草稿（必须带出处 citations），不接任何模型；调查员 `review` 后才写回目标实体（statement / timelineEvent）。

## 7. 与 C# 的对齐情况与建议（W1/W2/W3）

| 项 | 现状 | 建议 |
|---|---|---|
| W3 `EvidenceItem` / `CustodyLedger` | 已对齐（`confidentiality`、Review 事件、`case_id` 行字段）；C# 编译校验通过 | 若再改 ToJsonLine 键序，须同步 `service/mcis_service/evidence/service.py::custody_line` 并跑 `test_custody_jsonl_accepted_by_csharp_ledger` |
| W3 `CrossCheckRegister` | 已对齐（三态、批量确认只限一致项、动作名） | 增加 `ConfirmedInBatch` 的 JSON 序列化名 `confirmedInBatch`（契约已有） |
| W3 `SafetyRecommendationBoard` | 已对齐（`progressPct`、`verificationNote`、`column`） | C# 无内容编辑 API；若需要，建议加 `UpdateDraft`（仅 Draft） |
| W3 `Consultation` | 已对齐（`draftSha256`、Waived、关闭条件、动作名） | `ReportId` 服务端暂用 caseId；建议契约化为 `reportId` 字段 |
| W2 `Domain/Timeline` | 冲突 `trackKind` 用 `TrackKind` 枚举名 | 交付后由 `mcis-core align` 输出 `conflict` 契约；服务保留人工 `status/resolution` |
| W1 `Domain/Colreg` | 服务用种子数据，`colreg:evaluate` 返回 501 | 交付后在 `tools/mcis-core` csproj 加 glob 并实现 `colreg` 子命令，结果对齐 `colreg.schema.json` |
| 审计扩展键 | snake_case（`seq/role/entity_type/entity_id/prev`），与 custody.jsonl 风格一致 | C# 读取 audit.jsonl 时忽略未知键即可 |

## 8. 已知限制

- 无身份认证：角色由请求头声明，仅适合本机单用户演示；服务只绑定 127.0.0.1。
- 导入失败时已写入的证据文件不会回滚（数据库事务会回滚）。
- `sim/state` 为内存态，服务重启后丢失；`sim/commands` 同样不持久化。
- 契约校验在服务端用 jsonschema 运行时执行（422 `CONTRACT_VIOLATION`）；Unity 侧尚未接入 schema 校验。

## HTTP 核心错误边界（安全兼容切片，2026-11-12）

使用 colreg.router._core 的 HTTP 路由不透传 CLI 错误正文或未知错误码。BAD_REQUEST/BAD_JSON 仍为 422，NOT_IMPLEMENTED/UNKNOWN_COMMAND 仍为 501；CORE_UNAVAILABLE 为 503、CORE_TIMEOUT 为 504、CORE_NO_OUTPUT/CORE_BAD_OUTPUT 为 502；其余 CoreError 映射 CORE_ERROR/502。消息为固定提示，不包含本地路径、stderr 或核心返回的自由文本。成功响应与 CLI 行为不变。

这不是旧 `/core/align` 文件读取或身份问题的修复：旧路径入口仍在，仅适合既有回环单用户演示。停用或限制旧入口须单独记录兼容取舍；不得据本切片宣称可正式多用户部署。

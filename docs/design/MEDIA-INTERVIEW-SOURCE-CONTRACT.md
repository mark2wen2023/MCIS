# 图音核对与笔录来源衔接：只读合同设计

状态：设计草案，未实现关联读取聚合或写入；不开放持久关联。仅静态查阅源码，不运行应用、请求、测试或模型，不读取案例/种子/媒体。

## 固定依据

- 图音基线：`76d6c22c474172a28f7b2da9ae45021e8d573b82`。
- #99 来源展示依据：本地缓存 `origin/feat/interview-source-disclosure` 的 `3d783392e7f3187457d1d5bfba1e6efcbb6d9064`；不是本轮远端 PR 最新头证明，也未合入本设计分支。
- 以下源码路径按上述各自版本解释；设计不改变现有权限、请求、归档保护或 unknown 语义。

## 现有 API 可取字段

| 对象与接口 | 已有字段 | 源码依据及边界 |
| --- | --- | --- |
| 笔录 `GET /api/v1/cases/{caseId}/interview-compare/{recordId}` | `caseId/recordId`；`record.evidenceId/sourceSha256`：page 固定构造两键，值可为 null；防御性解析仍区分键缺失；陈述行有各自修订信息 | `service/mcis_service/interview_compare/router.py` 的 `page`：按既有内容权限及脱敏返回。此响应未提供整份笔录的稳定版本；不能用陈述版本代替。#99 `web/src/interview/SourceDisclosure.tsx` 仅展示声明和本案证据链接。 |
| 音频 `GET /api/v1/cases/{caseId}/audio-reviews/{runId}` | `caseId/runId/revision/initial/humanRevisions`；`initial.machineDraft.source` 的 `evidenceId/registeredSha256/currentSha256/stateDigest`；v3 采样数/采样率，另有片段 ID | `audio_review/app.py` 的 `source/check/result/get`。服务来源路径有读取字节及比较逻辑，本轮未执行；返回运行中的历史字段不能单独证明当前原件。`currentSha256` 须注明该来源快照语境，不能标成永远最新。 |
| 图片 `GET /api/v1/cases/{caseId}/image-reviews/{runId}` | `caseId/runId/revision/initial/reviews`；`initial.sourceVersions`、`bindings`；候选来源 PDF/页图/原始输出摘要、声明页码及逐行 `line_index` | `image_review/app.py` 的 `register/result/read`，`contract.py`。导入结果的 sourceVersions 有 evidenceId/sha256；`tasks.py` 本地任务 raw/candidate 可为只有 sha256/kind 的任务产物，不能补造 evidenceId。`pageMappingVerified=False`、真实性未核验。 |

图音列表接口明确 `sourceCheck=not-performed-by-list`，不能用列表代替详情核对。登记回执摘要、模型输出摘要和文件 SHA-256 含义不同，不可互换。图音 GET 现有来源检查可能阻止旧来源详情读取；不能假定已有独立、永久可读的精确历史解析接口。

“只读”仅指不创建业务关联，不等于零副作用：笔录 page 对非 LeadInvestigator/Investigator 的已授权读取可调用 testimony.read 写审计（router.py 的 page）。图音详情也可能读取原件字节并做来源检查；此处不承诺所有 GET 无写入或无文件读取。当前任务仅静态查代码，未调用这些接口。

## 最小声明比较合同（拟议）

只读观察应保留两侧原始值及其来源，包含：笔录 `caseId/recordId`，图音 `caseId/mediaKind/runId/reviewRevision`，逐项 `sourceRole/evidenceId/sha256`，摘要属于哪份记录及本次读取上下文。来源角色是原音、PDF、页图或机器产物，**不是用户权限角色**。

1. 两侧均须由各自现有授权读取。不可用只报告不可用，不推断资料不存在或泄露被限制的字段；不借任一入口扩大另一入口可见性。
2. 案件 ID 精确相等才可进入比较；跨案为 `case_mismatch`，不搜索另一案件。
3. 来源角色必须显式且可确定；笔录现有 evidenceId/sourceSha256 并不自行说明是原音还是 PDF。笔录来源角色无现成 API 字段，不得从正在打开的音频页反推。拟议人工声明须包含 role、basisText（判定依据）、declaredAt、所针对的 caseId/recordId/来源字段快照和声明者出处；页面演示身份不能冒充可信操作者。未建立此声明时为 `role_unknown`。声明绑定的案件/笔录身份、来源字段快照或已取得的版本任一变化，即失效为 `role_declaration_stale`，要求重新声明；旧声明仅作历史，不自动套用新快照。即使后来字段变回旧值，也不能自动恢复旧声明有效性。人工声明本身也不是来源验证；未来持久化须有服务端身份/版本/审计。角色不同为 `role_mismatch`，不得依文件名、文字或摘要猜角色。
4. ID 按下面独立字段规则判定；完整合法 ID 不同为 `id_mismatch`。不可静默修剪、改大小写或补造 ID。#99 的 EV 编号显示约束不是新增服务端授权规则。
5. SHA-256 仅接受完整 64 位十六进制；验证后统一 ASCII 小写比较，原返回值保留，不 trim。相同 ID 不同摘要为 `digest_mismatch`，不能称篡改。摘要对应字段须按下表，不能挑一个相等的摘要代替。
6. 只有同案、同来源角色、同 ID、同摘要才可标记 `declarations_equal`（来源声明一致）；**不证明原件真实性、字节当前仍可用、文本内容一致、人已阅读/听取、人工批准或笔录已引用该运行**。

分别保存读取状态（未读/可用/不可用）、字段与比较结果，以及关联状态（当前一律未建立）。不要压成一个“已核验”布尔值。多来源逐项比较，不以其中一项一致覆盖其他缺项。未知页码、未知时间、说话人未知保持未知；图片坐标/PDF页码声明不等于笔录字符或句子定位。

### 摘要对应与独立字段状态

| 声明角色 | 笔录 sourceSha256 的拟议比较目标 | 其他摘要的意义 |
| --- | --- | --- |
| 原音 | 固定音频运行 source.currentSha256 | currentSha256 是该来源快照记录的实际字节摘要；registeredSha256 是登记回执 sourceSha256。source() 检查二者相等，但二者语义仍须分别展示，不能在缺 currentSha256 时回退。stateDigest 是含案件、证据、requestDigest 和两个摘要的规范化状态摘要，不是原音摘要。 |
| PDF | candidate.source.pdf_sha256，对照 sourceVersions.pdf.sha256 | PDF 与页图分别比较；同角色内部两份声明不一致记 source_inconsistent，不任选其一。 |
| 页图 | candidate.source.image_sha256，对照 sourceVersions.image.sha256 | 图片摘要不能与 PDF 摘要互换，摘要一致也不证明 PDF→页图渲染关系或页码。 |
| 图片原始识别输出（image_raw_output） | initial.sourceVersions.raw.sha256，并核对 initial.candidate.source.raw_sha256 | evidenceId 仅取 initial.sourceVersions.raw.evidenceId；本地任务产物可能无此键，不补造。 |
| 图片结构化候选产物（image_candidate） | initial.sourceVersions.candidate.sha256 | evidenceId 仅取 initial.sourceVersions.candidate.evidenceId；不是 raw 摘要，也不是 candidate.source 内的 PDF/页图摘要。任务产物可能没有 evidenceId，保持缺项。 |

上表图片路径均在运行 initial 中（PDF/页图行省略 initial 前缀）。每个 PDF 或页图比较要求该角色的 candidate.source 摘要和 sourceVersions 摘要均存在且合法；任一缺失/null/非法为不可确定，不得仅凭另一摘要与笔录相等给出一致。要求多个角色的整体比较时，任一必要角色缺项也阻止整体一致。音频机器草稿/识别输出作为笔录来源的独立角色与路径尚未定义，不套用图片路径、不回退原音摘要，暂不可比较。

每个字段独立输出状态和原因，不以首个错误覆盖其他字段：键不存在为 missing；显式 null 为 unknown_null；空字符串为 empty；纯空白、外围空白、非法类型/格式为 invalid；合法值为 present。原始值保留。只有各必要字段均 present 且符合比较条件才可声明一致。不可用响应不继续解析或泄露其字段。

案件、笔录和运行 ID 作为各 API 的不透明标识精确比较，大小写敏感，不转换数值、不去前导零；不把图音与笔录各自不同的记录 ID 相互比较。证据 ID 的拟议可比较子集暂沿 #99 的 ^EV-[0-9]+$：EV-01 与 EV-1 不相等，ev-1 不自动转 EV-1。不符合此子集的已返回值仍展示为待核对，不声称服务器记录非法；该子集与服务端全部合法 ID 是否一致仍是接线前置。来源角色使用显式枚举，非法或缺失不能默认原音。

### 重复来源与多候选

- 不按数组顺序配对，不按文件名/文本/摘要自动找“最佳”运行。人工明确选择候选身份（caseId、mediaKind、runId、reviewRevision、sourceRole），再逐对比较；选择不是持久关联或批准。
- 同一载荷同一角色若出现多个来源，标记 duplicate_role/ambiguous 并保留全部项，即使 ID/摘要相同也不静默去重。未来若业务确需同角色多来源，须先增加独立来源项 ID，不能靠索引。
- 不同运行或核对修订是不同候选：同一来源 ID/摘要可对应多次识别，不合并为唯一运行。不因一个候选一致而忽略其余候选或缺项。
- 输出每对候选的字段错误列表、比较状态与选定版本；未选定、歧义或内部声明冲突时总体为不可确定，不给整体一致。来源 ID 与摘要均不匹配时两项分别记录，不把摘要错误隐藏在 ID 错误后。

## 分层与持久关联前置

1. 先实现不写业务关联的展示/比较层（保留现有读取审计）：双方已授权返回数据、固定上下文、明确未知；不自动选择、匹配、跳转写入笔录。
2. 如需持久关联，先补可解析的双方固定版本：整份笔录不可复用版本标识；图音 runId + 核对修订 + 片段/行定位；源记录角色、ID 与摘要。读取最新详情后在前端截取历史不等于可靠历史接口。
3. 服务端提交须在明确事务边界内核对双方版本及权限交集，关联与审计同事务；保留操作者、关联意图和旧记录，不能把当前来源补成旧史。跨存储、并发、恢复后 ID/版本复用、unknown 结果及操作回执协议均须先定，不能靠超时或刷新推断未提交。
4. 旧笔录缺版本/角色或旧史缺失保持未知；先验证历史解析、归档/恢复关联兼容和权限，再考虑开放写入。图音正式整包归档保护继续保持，不因设计新增类型而放行。

## 拟议合成验收（本轮未执行）

- 无网络纯函数：同案同角色同 ID 同摘要；摘要大小写一致但 ID 大小写不折叠；缺键/null/空串/空白/非法分别记录；多字段同时错误；音频 current/registered/stateDigest 不互代；PDF/页图分开；笔录角色无声明时未知、绑定快照变化失效且旧声明仅历史；PDF/页图任一必要摘要缺失或非法不以另一个相等通过；图片 raw 与 candidate 独立角色/路径；重复角色、乱序数组、多候选多修订不自动配对；显式选择一项不掩盖其他缺项。
- 合成前端：多运行、多修订、切案/切运行及迟到响应不误归属；声明一致不显示“原件已验/人工批准”，不自动写入笔录；缺失字段不表示原件不存在。
- 未来单独授权的服务验收：固定历史可读、版本变化不静默重绑定、关联与审计原子、权限交集、旧数据未知、归档往返。当前种子导入/后端启动暂停及既有受限测试禁令不因本清单解除。

尚未验证真实浏览器、HTTP、原件字节、生产身份或持久关联。本文件不是运行许可或上线承诺。

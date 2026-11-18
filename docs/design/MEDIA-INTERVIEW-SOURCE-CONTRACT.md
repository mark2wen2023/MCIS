# 图音核对与笔录来源衔接：只读合同设计

状态：设计草案，未实现关联读取聚合或写入；不开放持久关联。仅静态查阅源码，不运行应用、请求、测试或模型，不读取案例/种子/媒体。

## 固定依据

- 图音基线：`76d6c22c474172a28f7b2da9ae45021e8d573b82`。
- #99 来源展示依据：本地缓存 `origin/feat/interview-source-disclosure` 的 `3d783392e7f3187457d1d5bfba1e6efcbb6d9064`；不是本轮远端 PR 最新头证明，也未合入本设计分支。
- 以下源码路径按上述各自版本解释；设计不改变现有权限、请求、归档保护或 unknown 语义。

## 现有 API 可取字段

| 对象与接口 | 已有字段 | 源码依据及边界 |
| --- | --- | --- |
| 笔录 `GET /api/v1/cases/{caseId}/interview-compare/{recordId}` | `caseId/recordId`；`record.evidenceId/sourceSha256`，字段可能缺失；陈述行有各自修订信息 | `service/mcis_service/interview_compare/router.py` 的 `page`：按既有内容权限及脱敏返回。此响应未提供整份笔录的稳定版本；不能用陈述版本代替。#99 `web/src/interview/SourceDisclosure.tsx` 仅展示声明和本案证据链接。 |
| 音频 `GET /api/v1/cases/{caseId}/audio-reviews/{runId}` | `caseId/runId/revision/initial/humanRevisions`；`initial.machineDraft.source` 的 `evidenceId/registeredSha256/currentSha256/stateDigest`；v3 采样数/采样率，另有片段 ID | `audio_review/app.py` 的 `source/check/result/get`。服务来源路径有读取字节及比较逻辑，本轮未执行；返回运行中的历史字段不能单独证明当前原件。`currentSha256` 须注明该来源快照语境，不能标成永远最新。 |
| 图片 `GET /api/v1/cases/{caseId}/image-reviews/{runId}` | `caseId/runId/revision/initial/reviews`；`initial.sourceVersions`、`bindings`；候选来源 PDF/页图/原始输出摘要、声明页码及逐行 `line_index` | `image_review/app.py` 的 `register/result/read`，`contract.py`。导入结果的 sourceVersions 有 evidenceId/sha256；`tasks.py` 本地任务 raw/candidate 可为只有 sha256/kind 的任务产物，不能补造 evidenceId。`pageMappingVerified=False`、真实性未核验。 |

图音列表接口明确 `sourceCheck=not-performed-by-list`，不能用列表代替详情核对。登记回执摘要、模型输出摘要和文件 SHA-256 含义不同，不可互换。图音 GET 现有来源检查可能阻止旧来源详情读取；不能假定已有独立、永久可读的精确历史解析接口。

## 最小声明比较合同（拟议）

只读观察应保留两侧原始值及其来源，包含：笔录 `caseId/recordId`，图音 `caseId/mediaKind/runId/reviewRevision`，逐项 `sourceRole/evidenceId/sha256`，摘要属于哪份记录及本次读取上下文。来源角色是原音、PDF、页图或机器产物，**不是用户权限角色**。

1. 两侧均须由各自现有授权读取。不可用只报告不可用，不推断资料不存在或泄露被限制的字段；不借任一入口扩大另一入口可见性。
2. 案件 ID 精确相等才可进入比较；跨案为 `case_mismatch`，不搜索另一案件。
3. 来源角色必须显式且可确定；笔录现有 evidenceId/sourceSha256 并不自行说明是原音还是 PDF。角色未知为 `role_unknown`，不同为 `role_mismatch`，不得依文件名、文字或摘要猜角色。
4. ID 缺失为 `missing`，非法类型/格式为 `invalid`；完整 ID 不同为 `id_mismatch`。不可静默修剪或补造 ID。#99 的 EV 编号显示约束不是新增服务端授权规则。
5. SHA-256 仅接受完整 64 位十六进制；验证后可统一大小写比较，原返回值保留。缺失/非法分别为 `missing/invalid`；相同 ID 不同摘要为 `digest_mismatch`，不能称篡改。
6. 只有同案、同来源角色、同 ID、同摘要才可标记 `declarations_equal`（来源声明一致）；**不证明原件真实性、字节当前仍可用、文本内容一致、人已阅读/听取、人工批准或笔录已引用该运行**。

分别保存读取状态（未读/可用/不可用）、字段与比较结果，以及关联状态（当前一律未建立）。不要压成一个“已核验”布尔值。多来源逐项比较，不以其中一项一致覆盖其他缺项。未知页码、未知时间、说话人未知保持未知；图片坐标/PDF页码声明不等于笔录字符或句子定位。

## 分层与持久关联前置

1. 先实现纯只读展示/比较层：双方已授权返回数据、固定上下文、明确未知；不自动选择、匹配、跳转写入笔录。
2. 如需持久关联，先补可解析的双方固定版本：整份笔录不可复用版本标识；图音 runId + 核对修订 + 片段/行定位；源记录角色、ID 与摘要。读取最新详情后在前端截取历史不等于可靠历史接口。
3. 服务端提交须在明确事务边界内核对双方版本及权限交集，关联与审计同事务；保留操作者、关联意图和旧记录，不能把当前来源补成旧史。跨存储、并发、恢复后 ID/版本复用、unknown 结果及操作回执协议均须先定，不能靠超时或刷新推断未提交。
4. 旧笔录缺版本/角色或旧史缺失保持未知；先验证历史解析、归档/恢复关联兼容和权限，再考虑开放写入。图音正式整包归档保护继续保持，不因设计新增类型而放行。

## 拟议合成验收（本轮未执行）

- 无网络纯函数：同案同角色同 ID 同摘要；大小写合法摘要；字段缺失/null/非法；跨案、角色未知或不同、ID/摘要不符；多来源部分缺失。
- 合成前端：多运行、多修订、切案/切运行及迟到响应不误归属；声明一致不显示“原件已验/人工批准”，不自动写入笔录；缺失字段不表示原件不存在。
- 未来单独授权的服务验收：固定历史可读、版本变化不静默重绑定、关联与审计原子、权限交集、旧数据未知、归档往返。当前种子导入/后端启动暂停及既有受限测试禁令不因本清单解除。

尚未验证真实浏览器、HTTP、原件字节、生产身份或持久关联。本文件不是运行许可或上线承诺。

# MCIS 调查问题闭环增量提案（未实施）

## 依据及范围
用户 2026-11-13 原话：“调查员发现了先判断，然后再次核实，再把问题留下来集体讨论。”
本提案将这一实际工作顺序落实为产品工作流，不声称法规要求；会议参与人、签字、表决规则、必须讨论的范围尚未由用户确定。
只读查看本地 pr34-integration/tree 副本：W20 AgentReviewPanel.tsx 已把确认限定为陈述写回，并明确不等于事实或责任认定；agents/extraction.py 绑定来源摘要；W5 interview_compare/view.py 已有 revision、Superseded、stale；agent-draft.schema.json 为通用草稿合同。未刷新远端或做全量代码审查。

## 推荐增量：跨模块“调查问题卡”，而非扩充一个确认按钮
单一案件 issueId，按 issue revision 追加不可静默覆盖的记录。
- issue：标题、案件、发起来源（人工/模型候选/比对发现）、关联 W4/W5/W15 对象、负责人、当前阶段、未决问题。
- sourceRef：实体与版本/摘要、原件标识、页码/时间段/问答段、引用文本；引用匹配不代表内容为真。
- assessment：调查员初判、依据、相反证据、未知项、作者与时间、取代的旧版本。
- verification：核实目标、方法、取证/联系动作记录、结果、关联新证据、执行者与时间；不以空值表示“已核实”。
- discussion：本次讨论所依据的冻结版本快照、参与者记录、议题、意见及分歧、结果（形成意见/继续核实/暂不能判断）、记录人及人工确认信息。
- event：追加事件及 requestId、expectedRevision，防止重复提交和并发覆盖。

### 分离两个维度
流程阶段：发现线索 → 已初判 → 核实中 → 待讨论 → 讨论已记录；可由讨论退回核实，出现新证据可重开。
认识状态：待核实、得到部分支持、证据冲突、材料不足、调查组形成意见。禁止把“流程结束”自动映射为“事实确定”。
所有阶段均保留对问题的支持/反驳/无关引用。来源材料不因分析判断而被改写。
AI 草稿确认只接受该条提取或建议进入工作区，不等于完成初判、核实、集体讨论或定责。

## 接入点
- W4：证据页发起问题，回跳到原片段；新版本使有关判断提示需复核，不删除旧版。
- W5：矛盾比对创建/关联问题卡，复用已有版本过期机制；已有 Confirmed 比对不自动升级为“调查组认定”。
- W15：分析节点绑定问题卡及证据，区分假设/初判/讨论意见；不能让图上的连线成为无来源的事实。
- W20：LLM 提议初判候选、核实清单、讨论摘要；只有人员提交相应流程事件，AgentService 无权完成核实/讨论确认。
- W16：报告候选读取明确标记的人工意见版本；未决问题需显式呈现，模型不能消除分歧。

## 分阶段实现
A 合同先行：REQUESTS 登记跨包增量，issue schema、事件模型、来源语义、迁移和权限矩阵；保留旧 W5/W20 行为，不静默重命名 Confirmed。
B 最小功能：人工问题卡、初判、核实追加、讨论记录及历史；API 乐观锁/幂等；独立侧栏，在 W4/W5 提供入口。
C 联动：W15 节点和 W20 候选引用；旧版失效标记；拒绝/修改留痕。
D 归档与报告：版本化完整保存、原子恢复、历史和引用完整性验收后才启用；此前遇不可保存内容应明确拒绝，不能漏存。

## 验收清单
1. AI 发现矛盾仅形成候选，不能写入已确认事实。
2. 两次不同初判均可追溯；新判断注明替代原因。
3. 无核实记录不能标记“核实已完成”；允许记录“无法核实”及原因。
4. 笔录/AIS/CCTV 冲突全部保留，模型不自行择一。
5. 集体讨论可退回核实或保留不确定，不强制结论。
6. 原证据更新，旧讨论快照仍可回溯，新界面显示待复核。
7. 并发编辑返回冲突且无覆盖；重复请求不产生双份讨论。
8. AI/无权人员不得确认讨论结果；字段/API/导出均检查授权。
9. 非参与人员记录参会人不能冒充这些人的签署；参与者签字需求另行确定。
10. 来源不可访问时不泄露原文，仍保留受控引用和缺失提示。
11. 被驳回的 AI 摘要不能进入正式报告，人工改写仍保留来源。
12. 归档恢复后初判、核实、讨论、分歧、重开和版本关系全部一致；无支持时明确拒绝导出。

## 后续需业务确认（不阻塞纯手工记录原型）
- 所有问题都讨论，还是初判核实后仍疑难/重要的问题提交讨论？
- 集体讨论由谁记录确认，是否需要参与人逐一签认？不先做多数票或两人审核假设。
- 暂不能判断事项在报告正文还是附件呈现？

# 独立切片 IQ-1：人工问题闭环合同提案（非正式 API）

## 最小范围与非目标
新增 case-scoped 的人工调查问题工作区，不修改既有陈述、比对 Confirmed 的含义；不自动生成事实、不增加自动外部取证或通讯。首片不接 LLM、不接会议录音转写、不作电子签名、不实现法定审批。原法定工作仍在线下进行，本产品仅记录过程。
本文件是合同提案；实施前需 REQUESTS 登记，审定后才进入 contracts/openapi.yaml 和 schemas。下列 URI 和限额均为工程建议，不是已存在接口。

## API 草案
统一前缀 /api/cases/{caseId}/investigation-issues。
- GET /：分页列表（limit 1..100，默认20，服务端不透明游标）；按阶段/负责人过滤；输出概览，不含证据原文。
- POST /：创建问题。body={requestId,title,description,sourceRefs}；服务端分配 issueId、作者、UTC时间、revision=1；初始阶段 Observed。人工来源，不允许客户端冒充 AI 或集体意见。
- GET /{issueId}：读取当前视图及可见引用，ETag为当前 revision。无权引用隐藏内容并返回 restricted 标记，不能用页码/标题泄露原文。
- GET /{issueId}/events：按序号分页读历史，无覆盖接口。
- POST /{issueId}/events：提交 {requestId,expectedRevision,type,payload}；事务内校验权限、源版本及合法转移，追加事件并更新视图。没有通用 PATCH 或 DELETE。
- GET /{issueId}/discussion-packet?revision=N：只读议题快照（JSON）含对应问题版本、核实记录及引用可见性；不是正式报告或自动外发文件。
所有读写响应 Cache-Control: no-store。禁止跨 caseId 的 issueId 引用。

## 事件与状态规则
| 事件 | 前置状态 | payload 必需内容 | 结果 |
|---|---|---|---|
| RecordAssessment | Observed/AssessmentRecorded/Verifying/AwaitingDiscussion | assessmentText、supportRefs、contraryRefs、unknowns、supersedesAssessmentId（有前版时）、changeReason（修订时） | AssessmentRecorded；若原已待讨论则显式标记需重审，不能隐藏原议程 |
| BeginVerification | AssessmentRecorded/DiscussionRecorded | question、plannedMethod | Verifying |
| AppendVerification | Verifying | activity、result、outcome=Supported/Contradicted/Inconclusive/UnableToVerify、sourceRefs；UnableToVerify需要reason | 仍Verifying，结果不自动升级事实 |
| SubmitForDiscussion | Verifying | verificationIds非空、unresolvedQuestions（可空但需说明）、proposedAgenda | AwaitingDiscussion，冻结参与讨论的版本 |
| RecordDiscussion | AwaitingDiscussion | packetRevision、occurredUtc、participantsRecorded、recorder、summary、dissent、outcome=OpinionRecorded/MoreVerification/Undetermined | DiscussionRecorded；MoreVerification回Verifying并保留讨论 |
| Reopen | DiscussionRecorded | reason、newSourceRefs（可空） | AssessmentRecorded；历史不变 |

RecordDiscussion 的 recorder 必须为服务端当前身份，participantsRecorded 仅表示记录人填写的参与者，不等于这些人登录确认或签署。人数不作为自动法定有效性标准；不引入投票算法。是否每一问题都需讨论保留业务待确认，首片只支持提交讨论，不用自动转移强迫用户。
编辑描述、撤回错误录入等扩展需另立事件，不做静默覆盖。所有认识状态都是人工表述，服务端只验证结构/权限/版本，不验证世界事实。

## 数据约束建议
- title 1..200字符；description/assessmentText/summary各最多10000；单事件请求最大128KiB，超过413；sourceRefs至多100项；拒绝未知字段、重复JSON键、非有限数值和非法Unicode。
- issueId/事件ID/作者/序号/createdUtc由服务端生成，requestId为UUID；caseId使用现有合同；expectedRevision为正整数，bool不当integer。
- SourceRef={entityType,entityId,entityRevision,digest,locator}，locator使用类型化 page/turn/timeRange，不接任意远端URL；时间段start<=end且有限，单位明确。不同类型必须使用对应locator。
- supportRefs/contraryRefs只引用本问题可见且case一致的SourceRef；新来源版本不原地改变旧引用；缺失/无权/过期分别表示，不自动删记录。
- sourceDigest是内容版本标识，不是公证或真实性证明；内容摘要如何计算复用各实体已有规范，不重新发明canonicalization。
- 事件序号连续，前事件摘要可辅助检测修改；不把哈希链当防管理员篡改的安全保证。
- 讨论快照包括issue revision和来源版本；与最新版本不同必须返回stale=true，并阻止按旧快照提交，用户重新核对后再提交。

## 权限与一致性
权限使用能力而非新增法定职级：issue.read、issue.record_assessment、issue.record_verification、issue.record_discussion。首片对应现有角色时应明确配置并做服务端拒绝测试；不能用前端按钮隐藏代替鉴权。
AgentService 不获得以上写事件能力；未来独立 issue.propose 只能创建待审候选，不能修改案件流程。现有身份请求头只是本地演示约定，不宣称真实认证。
expectedRevision不匹配→409 REVISION_CONFLICT，不写事件；相同case/actor/requestId与完全相同规范请求→返回原结果；同requestId不同内容→409 REQUEST_REUSE。幂等回执、事件及当前视图同事务提交；失败回滚。
记录动作超时，客户端先按requestId读取结果（拟 GET /operations/{requestId}，同scope授权）而非直接重发；UI保留“结果未确认”。读操作不授予跨角色回执访问。
权限不允许→403且不得附含是否存在的敏感元数据；权限允许但案件/问题不存在→404。参数错误→422；不可转换状态→409 INVALID_TRANSITION；内部失败→500且不回显原证据。

## 归档边界（首片必须明确处理）
问题卡是案件数据。其任何记录存在时，若当前.mcase不能无损保存全量事件、视图、来源版本及幂等回执，应明确拒绝导出；不得仅导出当前卡片或忽略记录。提交实施前必须决定是同步实现归档扩展，还是把首片标为不可归档并要求用户知情确认，不能偷偷破坏现有归档体验。此处不分配版本号，避免与W7/ECFC竞争。

## 分层验证计划（尚未执行）
A 合同测试：约束边界、重复键/字段、非法时间/Unicode、跨案引用、未知枚举、整数布尔混淆，拒绝无关字段。
B 状态机测试：全部合法边与非法边；反复核实/讨论退回/重开；Inconclusive及UnableToVerify保留；旧初判不覆盖。
C 事务测试：事件写入失败、视图更新失败、回执写入失败均完整回滚；双客户端同revision只有一个成功；同requestId重试不重复。
D 权限测试：全角色矩阵、AgentService禁写、跨案issue/回执、隐藏来源与no-store；权限变更后的浏览器缓存清空。
E 跨模块测试：W5 Confirmed不自动构成集体意见；W4版本更新标stale；W15引用记录有来源；W20拒绝候选不进入问题结论；W16不能把待讨论项写成已认定。
F UI实测：取消/返回/重载/重复点击/断网后查询；讨论显示各版本与分歧；切换案件和身份清空旧内容。
G 归档测试：按最终确定策略验证明确阻断，或完整往返/损坏包/超限包/恢复原子性；没有此项不得声称整案备份支持。

## 交付与验收措辞
首个设计草稿：本文件，无运行功能；实现切片：合同+存储+人工UI/API+自动测试；可合并候选：独立验收及真实浏览器、跨模块与归档策略通过；生产交付仍需要真实认证及单位流程确认。不得把此测试计划的条目数当成已通过测试。

## 用户补充：调查认识随证据递进而变化
2026-11-13 用户说明：前期证据可能导向一种判断，后期信息增加可能导向另一判断。故应采用“按当时所知重现”的时间视图，而非只存最新结论。
- 每次初判/讨论意见固定其 knowledgeCutoffUtc、实际引用的 source versions、作者理由和未知项；knowledgeCutoffUtc 只是记录边界，不代表当时已掌握所有可能证据。
- 新材料生成 ChangeImpact 候选：新增/替代来源、可能受影响的 assessmentId、支持/反驳/无法确定及引用。AI 只提议影响，不能自动改初判或结案。
- 需要复核标记和流程阶段分离：newEvidencePendingReview=true 不自动把 DiscussionRecorded 重写为其他状态；人员确认重开后才产生 Reopen 事件。
- 修订必须同时保留旧判断、旧依据、新证据、变更理由和替代关系；“判断被推翻”不等于原人员存在过错，界面中性显示“基于新增材料修订”。
- 时间视图两栏显示“当时已记录的信息/此后增加的信息”，不将事后资料偷偷注入早期判断的依据。
- 新验收：新证据到来不改变历史快照；AI提示不直接改流程；人工选择保留原判断必须写说明并留下相反证据；矛盾无法消除则保留未决；讨论后重开不删除原讨论记录。

## 用户确认补充：并列可能性，逐项核实，再集体讨论
问题卡需保留多个 Hypothesis 候选，而不是只容纳一个初判文本。每项具有 hypothesisId、版本、表述、提出者/来源、支持/反驳引用、未知项、核实任务及结果。人工可以新增或修订，不把否定的可能性删除；Rejected/Unsupported 只表示该轮证据评价，不是绝对不可能。AI 同样只能提出候选。
Verification 事件应引用 hypothesisId+version 与 verificationRound；本轮提交讨论前，逐项列出该轮选定待核实假设的结果，包括明确的 UnableToVerify/Inconclusive。不能因为一个假设完成核实，就自动把其他假设视为已核实。新假设或版本变化使关联讨论快照过期。涉及哪些可能性需要再次核实由调查人员明确记录，不由模型自行隐藏其他可能性。
建议追加验收：两个假设相互冲突仍可共存；一个有支持、一个证据不足均进入议题；新增第三假设不消除前两项；改写假设保留原版本；旧版本核实不得自动用于新版本；全部未知也可记录为集体讨论的未决结果。
此多假设结构目前仍属合同设计，内存原型未实现，不能声称逐假设核实已落地。

## 原型缺陷修正记录
独立审查发现：MoreVerification 或 Reopen 后可复用旧核实记录直接提交讨论。现有原型增加 verificationRound 及本轮 verificationIds；退回核实开启新轮、清空当前轮索引但保留全部历史事件；重开后再次 BeginVerification 建立新轮，必须有本轮新核实记录。议题快照记录核实轮次；重复幂等回执不重置新轮。新增三项回归，合计17项标准库测试通过（非独立复验）。
权限限制：actor=='AgentService' 只用于测试夹具，并非可信身份类型检查；其他字符串可被调用方冒充。原型没有认证、服务端授权中间件、持久事务或并发锁，不可用于真实系统。

## 低负担交互补充：先自动并排对照，再按需建卡
用户澄清实际办案难以逐条手工填写精细证据可靠性表，系统应提供时间线对照工具。问题卡不是所有证据的必填入口：先展示自动提取的多源时间线、原文/片段和来源跳转，再由调查人员把需持续跟踪的疑点选入问题卡；普通浏览和比较不要求填表。
原始时间、来源时区/时钟依据与有证据支持的校时版本并列保留。自动建议校时必须带计算依据、适用范围、误差/未知和来源，人工确认才应用为分析视图；不得覆盖原始时间，不能把缺失时间伪造为确定时间。多个校时假设可并列，时间接近不自动证明同一事件。
问题卡界面尽量预填已有case/sourceRefs/片段，人员只补当前必要的判断、核实记录及未决点；复杂字段折叠展示。不能强制给每条证据打可靠性分数或填写固定精细表格。
新增验收：不建卡也可查看多源并排时间线；原片段可回跳；接受/拒绝校时建议都有记录；撤销校时仍保留原始时间和历史；无依据不自动校时；由疑点创建卡片不复制或改写原证据；批量提取结果不自动创建海量待办卡。

> 历史证据归档（2026-11-14），不是当前授权或可执行说明。未在本次归档重跑原测试/模型；旧raw-key路径已在498f807禁用，真实执行仍HOLD。来源、原始摘要和归档摘要见MANIFEST.json。

# 专家群真实 DeepSeek + Pi：断点审计与最小计划

2026-11-14，仅代码审查与离线准备。没有实现新专家群、调用模型、查看实际凭据、推送、改动其他分支、合并或部署。隔离审查快照为PR56 `254167e3e957784fd9d2d136a275731f33314d9b`；正式main基线`3aba2bf03e393909c611489ae573a887087637ac`。本报告不能替代后续外发授权。

## 已有能力与断点

| 链路 | 实际代码与证据 | 不能据此声称 |
|---|---|---|
|正式六角色登记|`agents/router.py:31-55`为REGISTRY；仅people_ops可配置，其余not_connected；`AgentOverviewPage.tsx:26-30`只读登记/队列，明确主会话和调度未接通|六个运行中的专家、聊天、任务进度/心跳|
|正式抽取按钮|`agents/router.py:247`仍调用`model_client.complete`；`model_client.py:22-38,41-63`限定loopback单次completion并拒绝工具调用|真实官方DeepSeek+Pi工具链|
|种子与工程替身|`seed/lily_mary.py:480-498`有虚构骨架草稿；`test_agents_w20.py`用固定替身/本地假HTTP服务器|模型能力或运行完成|
|Pi实际循环+模拟provider|`tools/pi-transcript/fixture-integration.mjs`真实Agent循环但固定三轮返回，realModel=false|真实模型执行|
|历史真实公开源闭环|`tests_acceptance/PI_PUBLIC_UI/LIVE_RESULT.md`及public-ui-5d3b415b receipt记载3请求、2工具、6提案；仅YANGZE22损害段|完整案件、多角色群、专家审查、生产登录|
|上述UI/人工步骤|`web/tests/pi-public-ui-live.tsx:62-79`是HappyDOM；needs_verification由scripted_test写入|原生浏览器或真人判断|
|Skill版本后的断点|`tests_acceptance/PI_SKILL/REPORT.md:18-20`：7dac16e4为3模拟轮/2工具/1提案、providerRequests=0；明确旧真实5d3b不验证新Skill版本|当前版本真实模型验收完成|
|公开源盲测|semantic_support的36c8/33ac历史真实记录是单Pi Agent的11/8项预测|专业角色协作、多真人独立意见|

特别注意：`web/tests/pi-independent-fixture.ts:4`直接构造remote-deepseek、inferencePerformed:true、fixture:false字段。仅检查结果字段或模型名无法证明真实调用；必须关联可信运行入口、实际请求回执、版本、输入/输出摘要及终态。现有回执也不是签名或对提供方底层模型身份的独立认证。既有失败和终态未知记录应保留，不能被后续成功覆盖。

## 可复用组件与不能直接复用的部分

- Pi1.5.2依赖由tools/pi-transcript/package-lock.json固定；runner提供预算、工具白名单、顺序执行和已验证候选完成标记。
- Python remote host持有canonical history、工具callId和源绑定，按显式disclosure摘要授权；模型不能提供任意history替代它。
- DeepSeek transport固定官方HTTPS目的地、禁止重定向、请求/响应上限及总deadline。当前transport使用trust_env=True；后续真实运行应披露和核查批准的代理路径，不能把这一点说成完全无环境代理。密钥只进受信主机内存/非回显输入，不进JS、argv、仓库或回执。
- 现有三个工具是单笔录式source read/search/validate，Skill也固定为陈述抽取。它们不是通用群调度API，不能换个角色名就当专业专家。公共报告适配必须标为public_report_excerpt，不能伪装真实证人笔录。
- semantic blind host更适合固定公开片段研究，已有sourceText哈希、隐藏参考建议、schema验证和不会激活事实的边界。也仍是单Agent，需要独立角色合同及聚合预算，不能静默泛化原允许名单。
- 旧草稿确认`_apply`、时间线写回、假设归档及生产角色头路由不应成为本切片输出路径。相关身份与原件安全由其他开发线处理。

## 建议最小切片：两角色公开片段审读，确定性协调

这是未来实现建议，当前尚未实现。第一版不做六角色全家桶、不建自由聊天或自动调度生产案件。

1. 固定一个已经获准公开使用的报告页段包（建议先用既有YANGZE22损害摘录），人工核对原PDF/页号、准确摘录、来源URL和SHA。本轮不重新下载或认证旧摘录；未来真实运行前需完成该检查。材料只含公开片段，不读取案件库、私人笔录或凭据。不把参考标签/人工答案发给模型。
2. 定义两个固定研究角色：A“来源与对象归属审读”，B“限定词与推断边界审读”。这是多角色模型分析，不是两名独立真人专家。两角色分别在独立Pi会话中读取同一冻结来源和问题，不看对方答案；不得暗改现有aggregate（其登记输入为已确认结论）或冒充全部六专业角色已接通。
3. 各自固定roleId、prompt/Skill/schema版本与摘要、工具白名单、输入摘要。结构输出为itemId、sourceSpan/逐字quote、sourceReportedClaim、proposedInterpretation、supportProposal、uncertainty、needsHumanReview。引用匹配与结构检查只证明格式/定位，不证明语义正确；未知或材料不足必须可显式返回。
4. 协调器只记录状态/限制和并列输出；按itemId建立差异表，保留双方原始解释，不投票、自动融合或生成“专家共识”。无第三次汇总模型调用，避免把未经核实意见再包装成事实。
5. 最小端到端输出是一次groupRunId关联两个childRunId的受控本地审读记录及可查看来源的结果页/导出。首次可用受信CLI/本地只读展示验收运行链；正式agents页面只读接入是下一门槛，须等待身份接口成熟，不能把离线记录当正式群会话。界面必须关联本次runId，不能复用种子结果冒充完成。

建议限额：复用现有Pi每角色最多4模型请求、8工具、120秒；协调总额最多8请求、16工具、240秒，两个子任务顺序运行。超限/取消关闭后续调用；没有自动重试/换模型/模拟回退。实际采用模型ID和允许的总预算需在运行前确认；不是本报告授权。官方端点、片段全文/摘要、两个角色、后续工具结果及模型输出将再次外发等范围必须一起披露。

## 状态和证据合同（待实现）

状态至少区分prepared、authorized、running、validated_pending_review、failed、cancelled、outcome_unknown。终态未知不自动重试；第二角色失败时第一份记录仍保留，但整组不能显示完成。

每组/子任务记录：sourcePacketDigest、role/Skill/schema版本摘要、Pi精确版本、配置provider/model、modelIdentityVerified=false、真实请求尝试与返回编号、tool callId、输入/输出摘要、预算使用、mock标志、终态及清理确认。日志不含密钥/完整提示，源材料和模型内容仅存明确授权的本地结果工件，不能以“回执”名义隐式上传。工程fixture和真实run使用显式模式且不能互相回退。

未核实状态必须贯穿展示/导出。人工备注若加入，只写未认证审读意见；页面勾选、双角色一致、schema通过均不能更新案件事实、证据、时间线、假设或正式报告结论。既有专家群页面不宣称真人身份或专业资质。

## 分阶段验收计划

A. 离线门禁（不计模型能力）：
- 精确role白名单/冻结版本，源文本和引用码点不被清洗；恶意来源指令不获得shell/file/network工具。
- 每角色独立上下文；源摘要/角色变更要求重新授权；跨run/callId重放、重复启动、迟到工具回包和错误final marker拒绝。
- role失败/取消/预算耗尽/超时/未知终态不显示完成；同一进程总预算不能按角色重置后越界；fixture绝不读key或发网络。
- 引文/数值/主体/限定词分别检查；部分提案无出处应拒绝或保留明确失败，不能静默丢弃后声称完整成功。
- no-fact-write与无敏感外发断言；对固定输入比较数据库/生产文件前后无修改。模拟测试保留mock标记，不据此给能力分数。

B. 单次真实验收（当前禁止执行）：
- 实现与版本冻结后独立安全复核；取得该公开片段、两个角色、模型/目的地及总预算的明确外发授权。
- 使用真实DeepSeek与实际Pi工具循环，禁止预设输出/MockTransport/fixture fallback；逐角色记录真实请求和工具关联。仅有realModel字段不够。
- 独立复核每条输出的原文定位、对象归属、限定词与推断边界。原始错误/缺项/分歧如实保留；没有人工标准不能给“专家准确率”。同一模型的不同角色不是独立专家样本。
- 两个角色都终态完成且结果工件完整才通过运行链验收；一轮不是全案质量、稳定性或行业专家能力验收。未知终态停止，确认后再决定是否另行授权下一次。

C. 正式UI验收（另一个门槛）：
- 接入既有agents页的真实runId/角色状态和只读出处，不引入假发送框/虚构进度。角色/案件切换、取消、迟到响应、失败恢复、导出实际文件须在开启沙箱的真实浏览器验证。
- 当前浏览器沙箱不可用，HappyDOM只算交互工程测试。生产身份与证据安全接口未完成前，不把该能力接入内网或旧头身份路由。

## 本轮实际离线检查

在新的detached254167e副本执行12个相关测试模块；外置pytest插件`no_egress.py`禁止AF_INET/AF_INET6连接，允许进程内部socketpair。未查看实际凭据，未运行live/probe/模型命令。

结果：**224 passed、1 failed**。失败是`test_agents_w20.py::test_real_http_protocol_fake_server_not_real_model`，它明确启动127.0.0.1假HTTP服务器，测试连接被本轮护栏拒绝，返回500而非预期201。保留原始失败、不修改断言或放松护栏；不是本轮发现的生产模型故障，更不能算真实模型请求。其余均为离线/模拟工程测试。原始日志offline-tests.txt与插件同目录。未安装/运行Node Pi完整套件，不借历史Node结果充当本轮结果。

独立只读代理复核正式入口、模拟标记、历史真实receipt与Skill版本断点，结论一致。审查快照未修改产品代码；本轮交付只有此计划与离线证据，不声称新功能已实现。

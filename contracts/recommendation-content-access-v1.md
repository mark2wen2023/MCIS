# W7 原文访问隔离 v1（安全修复，先于 W7.4 UI）

基线 main276fe2529432041d5d0d242bf28a7d108c44ffde。仅合成复现：默认 Public 的 recommendations=ReadOnly，既有 detail/list/board 可返回 Draft 正文、全部回复及派生摘要。不是已发生真实资料泄漏的证据。

## 临时保守门槛
原文没有可靠字段来源/公开审批分类，Issued 不是公开许可。复用 reports.access.require_content 的完整策略验证，不改变策略矩阵：仅 LeadInvestigator/Investigator；全部类别须明确 ReadOnly/ReadWrite；适用于该角色的任一已知字段脱敏规则即拒绝；损坏/未知策略、缺失类别、Redacted/Deny 均 fail-closed。新 helper 拒绝非 SQLite（不承诺其他数据库的撤权互斥）。建议写操作另须 recommendations=ReadWrite；征求意见写另须 report_draft=ReadWrite。

默认仅首席可访问；默认 Investigator 因 medical=Deny 和字段规则被拒绝，这是有意的兼容收紧，不自动授予其更多权限。不提供部分脱敏输出或自动公开。该门槛并不证明原文准确、保密等级正确或身份真实；本地角色头仍非生产认证。

## 覆盖
- recommendations list/detail/board 和所有创建/修改/transition/responses 返回原文的写入口：读取源前准入；history 同时要求 audit。
- consultation 全部读写原文端点（评论、回复、放弃理由等）；防同模块旁路。
- 单建议及通用 audit：结构化/原始 line 任一 SafetyRec/Consultation 类别、recommendation/consultationRound 实体或 safetyrec./consultation. 动作即原文相关；损坏、重复键、非有限数、冲突标记按相关处理。孤立事件也保护，不依赖原行存在。报告/笔录已有 guard 保留。
- package export：组装文件/写 export 审计前检查建议、征求意见及残存相关审计。无这些内容的案件不加本门槛。
- legacy import：含建议/征求意见/相关审计时，在任何 SQL/blob 写入前以目标库现有/默认权限检查调用者；不能用包内 access-policy 授权。无这些内容不受此门槛影响。含这些原文的旧包仅接受缺省或等于系统默认的策略，非默认包策略422拒绝而非悄悄授予/改写。对应含原文且非默认策略的源案件出口409 RECOMMENDATION_POLICY_RESTORE_UNSUPPORTED，防产生该路径不能安全恢复的假备份。恢复后原文出口仍执行本门槛。受限 intake 已拒绝非空建议/征求意见；保留其约束。
- 派生报告已有同等或更强全文门槛，保持并回归，不重写专业内容。

## 撤权与并发语义
复用成功 BEGIN IMMEDIATE 和既有 reserved-writer 证明，政策/来源读取与结果准备在同一 SQLite 事务。先取保留锁的读取可完成；撤权提交后新读取拒绝。客户端已收到的字节无法追回。无模型、网络请求或下载跨事务；既有包本地读写仍在受控路径，不引入外部 IO。没有增加 Python 外层锁或改变既有锁序。

本修复不提供正文修改的 CAS/幂等回执，不修称旧 UI 写入的未知结果；W7.4 编辑继续禁用。无部署/W11/对外通信。

## 专业依据
IMO MSC.255(84) §1.1（预防而非归责）、§13.5（核对准确完整）、§25.2（报告草案披露需保密保证）支持原文核查和保守准入，但本功能不是完整法规合规认证。
https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MSCResolutions/MSC.255%2884%29.pdf

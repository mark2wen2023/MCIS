# 报告句级媒体绑定：内部合同草案（实现阻断）

代码依据固定于 3e6d8729e75ce68b8ea0a0d0f2741721a2ebb1d9，candidate/audio-reference-range。本轮仅静态审查，无应用/测试/存储执行；不是新增产品绑定功能。现有报告格式、导出、投影及摘要全部不改。

## 已有身份不是不可变内容版本

- service/mcis_service/reports/service.py:96–126 create_report 由服务器生成 reportId；familyId/parentReportId 连接生成谱系，version 为同 family 的生成序号。
- 同文件 :172–223 review_section 在同一 reportId 上更新句子/章节和报告状态，然后 put_doc；没有增加 report.version。:180–183 按 sectionId/sentenceId 查当前句子；:198–203 整节修改将全部句子替换为 sectionId+'-investigator'。同 ID 的后续整节修改可再次改变正文。
- service/mcis_service/db.py:96–106 put_doc 更新现有行，:109–110 约束只是 case_id+key 唯一。不能把 get_report 当前行当不可变历史版本。
- contracts/schemas/report.schema.json:58–60 version 只要求正整数，:123–125 sectionId 和 :220–222 sentenceId 是字符串；未提供复核内容版本字段。地址可被服务器识别，不等于历史正文永久不变。
- reports/service.py:79–92 的 RA 快照有 reportId/sectionId/sentenceId、beforeValue/afterValue/auditSeq；生成时 after 是完整报告，复核时 :214–219 是去掉 reviews 的目标对象，导出时 router.py:148–150 是状态/格式/摘要。get_snapshot (:240–244) 只按同案 ID 返回快照，没有统一“某固定报告状态的完整句锚点”解析合同。不能一概把 RA 当完整历史报告，更不能凭最新 auditSeq 反推版本。

结论：已有生成 ID/句锚点可以复用为地址，但目前不足以满足“服务器固定报告版本下不可变句子绑定”。仅在纯函数中再算当前正文摘要不会建立可信历史存储和版本身份，故本轮不增加这样的假绑定单元。

## 后续内部合同的必需语义（未定案、非可上传 schema）

1. 信任入口：只能是服务端从同案授权且一致的读取视图取得的报告历史对象、精确媒体引用与审计。不得用客户端自报 role、revision 或 SHA 授权，也不得用相同正文推定同一次绑定。
2. 报告侧地址复用 caseId/reportId/familyId/version/sectionId/sentenceId，但必须再有已定义的不可变内容状态来源。优先评估现有 RA 生成/复核快照能否在不改原义下提供该来源，明确事件类型、before/after 方向、载荷层级及句唯一性；此解析尚不存在。不能把 updatedUtc、最大序号、数组下标或新增任意 UUID 当已经实现的产品锚点。
3. 媒体侧复用现有 exact-media-report-reference/1：同案 evidenceId/runId/revision/segmentId 与来自可信旧引用的 referenceSha256。保持旧摘要配方，不在其中偷偷加入报告字段；文件内范围不是事故时刻。
4. 绑定对象必须与明确的报告内容状态对应，不能按 familyId 自动迁移到新报告，也不能因同一个 reportId/version 被复核而静默替换。旧状态仍指旧媒体摘要；新状态只有经独立确认产生自己的绑定。没有绑定的旧报告保持“未绑定/不可定位”，不查询 latest、不补造旧历史。
5. 本草案不定义数据库表、迁移、写入操作或对外字段。正式存储/审计原子性和允许创建绑定的调用点仍待授权设计；一个内存 dict 不能声称服务器已生成或持久可信。

## 手造正常期望（说明素材，不是产品 fixture 或已执行测试）

以下标识纯说明，未注册、未持久化；H1/H2 是符号，不冒充真实 SHA。

| 场景 | 手造选择 | 所需期望 | 当前是否可验收 |
| --- | --- | --- | --- |
| 第一生成报告 | 同案 C-SYN，RPT-SYN-A / family RPT-SYN-A / version 1 / section S / sentence Q；媒体 E/R/revision 1/segment T/H1 | 经可信固定内容状态建立 B1 后，旧句仍锁 H1 | 不可；B1 的可信内容状态入口尚缺 |
| 重新生成 | 同案 RPT-SYN-B / parent RPT-SYN-A / version 2 / S/Q；媒体 revision 2/H2 | B2 独立于 B1，读取 A 不改用 H2 | 不可；不通过假存储桩声称完成 |
| 同版本人工复核 | RPT-SYN-A/version 1 的 Q 改文或整节替换成 S-investigator | 原绑定不得误挂到新正文；旧锚点缺失/不同内容须明确区分 | 已有源码证明可能发生，但没有执行复核或端到端测试 |
| 旧报告没有绑定 | 仅已有 evidence 引用 | 保留未绑定，不猜 run/revision/摘要 | 仅合同期望，本轮未接入 |

## 最小后续，不重造报告系统

先只读定义并复核现有 RA 快照到“固定目标状态”的受限解析规则，区分完整生成报告、句级/节级复核、导出元数据，证明来源与所属报告/案/句在同一读取视图中可确定；未知形状保持不可用。尤其需说明整节替换、重复句 ID、同生成版本多次修改如何区分，不能通过临时新增版本号掩盖现状。

只有该语义被确认后，才可做独立纯逻辑正常输入测试：旧状态→H1、新状态→H2、再读旧状态仍 H1；再另行讨论可信绑定的服务端生成/持久事务和权限交集。当前不需要新报告系统或改变默认导出，但也没有安全理由实现一个声称已固定句子的绑定函数。

本轮未运行服务、Save、权限/故障/恢复/ORM/浏览器/模型或任何暂停测试，未读取原案/seed。文档静态自检通过不等于这些场景运行通过。保持原接口、main、mcis-3d 和部署不变。

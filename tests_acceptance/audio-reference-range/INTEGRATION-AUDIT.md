# 报告旧音频范围接通前静态审计

固定代码：763c5f1cbb1dddb4e41750cac91b30fe2a4d97a5；candidate/audio-reference-range。行号均指该头。本轮仅查看受版本管理源码和合成验收记录，未执行应用、SQL、测试、请求、保存、恢复或原音读取。范围限于以下入口，不声称全仓穷尽。

结论：**尚无可直接接通的现成调用点**。保持内部纯读取候选，不能据此接路由、前端、媒体下载或恢复。需先建立可信报告绑定、授权交集、同一读视图与原采样基准来源。

## 代码依据与保障

路径相对于 service/mcis_service/。

| 文件/符号/行号 | 已有行为 | 缺失或未证明 |
| --- | --- | --- |
| common/context.py:27 get_ctx（说明 :1） | HTTP 头解析角色/操作者，默认 Investigator | 不是可信生产认证；不得把头当已认证身份，本轮未注入角色 |
| reports/router.py:29 check_access；reports/access.py:30 require_content | 按案策略、完整内容类别/字段规则、调查员和 report_draft 检查 | 不等同媒体 SAFE_ID、案件存在与 Restricted 来源检查；角色名相同不等于授权交集 |
| reports/router.py:92 get_report；reports/service.py:53 get_report；db.py:87 get_row | 同 Session 按 case_id+report_id 取报告并深拷贝；pending 不返回正文 | 未核媒体行/来源或精确媒体绑定，不是媒体引用重开验收 |
| reports/router.py:139 export_report | WRITE_LOCK+Session，授权后读取报告、渲染、append_operation，再退出会话返回字节 | 有审计写入，不是纯只读；没有调用精确媒体范围读取 |
| reports/service.py:79 append_operation、:240 get_snapshot | 同案报告操作审计及快照 | 未见固定媒体 case/evidence/run/revision/segment/摘要的持久合同 |
| reports/sources.py:189 build_sections，:196、:200 ev_citation | 全案证据清单与 evidence/id 引用、需复核标记 | 非媒体精确引用；不能据此猜修订或以 latest 补齐 |
| evidence_intake/router.py:24 authorize | 调查员、SAFE_ID、load_case；evidence_meta/testimony 完整读取和 Restricted filter | 业务授权非认证，也不替代报告授权 |
| evidence_intake/router.py:90 load_receipt，:118–139 | 同案 EvidenceRow、唯一 Register、登记绑定/字节摘要/保管记录核对，返回原字节与派生证据 | 读取文件并调用 preview，不是纯元数据读取；文件系统不被 SQLite 事务锁定 |
| audio_review/app.py:39 source、:54 sample_source、:57 matched_source、:105 attach | 完整有界 PCM 核验，实际摘要与登记匹配；保存 frames/rate；v3 显式源时基，v2 要求整数毫秒 | 初始 audio 元数据未被旧引用摘要独立完整绑定；旧/恢复行必须另有可信来源 |
| audio_review/app.py:73 check、:133 get；audio_review/tasks.py:48 verify_task_binding | 同会话 begin+authorize 后取同案/run 历史并核 source；导入草稿核原稿，任务型核成功任务和产物关联 | 不是精确单修订接口；会读取文件，不能直接作为纯范围读取。v2 matched_source 不直接比较 initial.audio，未来组合还需显式对照重新取得 fmt |
| audio_review/app.py:138 revise、:153–161、:165 register_audio_review | 保存文件内毫秒、operator_declared/unknown，修订与审计同事务；注册时建追加保护触发器 | 不证明恢复来源、外部文件稳定或事实核验；本轮未执行 |
| evidence_intake/router.py:221 download | 初步 authorize 后再在 WRITE_LOCK+新 Session+begin 内授权、load_receipt、protect_container，并追加 Access 保管事件 | 有写入副作用；独立下载请求不是前次报告视图，没有报告 revision/segment 自动绑定 |
| reports/media_reference_reader.py:36 read_revision、:46 read_evidence；evidence/service.py:147 report_source_snapshot | 调用方 Session，no_autoflush，下按同案精确行/证据派生读取，无文件或审计写入 | 不建立事务/授权/源字节保证；no_autoflush 不等于一致快照 |
| reports/audio_reference_range.py:11 _ObservedRead、:31 read_exact_audio_range | 捕获一次精确读的行，必填旧摘要、核 segment 和时基；范围或明确未知 | 捕获 Python 行不能补救上游混合视图，不给予访问许可或证明原音 |

## 会话、文件及恢复边界

- db.py:41–51 设置 SQLite WAL/foreign_keys，未在此显式统一隔离级别；:67–76 每个 session() 新建 Session，退出 commit、异常 rollback、最终 close。跨上下文/HTTP 请求不属于同一视图。
- reports/access.py:15–23 begin() 仅在 SQLite driver_connection 尚未 in_transaction 时执行 BEGIN IMMEDIATE，记录事务/连接/线程凭据；已经在事务中不会升级或新记凭据。未来须从明确新会话、首个策略/来源读取前建立边界，不能仅凭调用过 begin() 宣称预留写事务成立。
- 报告 get 经 require_content 调用 begin，export 另持 db.py:37 进程内 RLock；音频 get/source_context 也 begin。各自事务存在，但当前无单一路径把可信报告绑定、精确媒体行、证据摘要和必要策略/来源检查一起完成。真实驱动/ORM组合未验。
- audio_review/_assembly.py:25–28 有研究用预留写凭据核对，可借鉴审查条件，不可把全量归档流程当报告接口；:115 仍 export_allowed=false/restore_ready=false。RLock 不是跨进程文件所有权；数据库事务不保证未来下载时文件不变。
- working_records_archive/service.py:17–21 白名单没有音频修订/任务等表；:41–50 对实际未知有记录表拒绝。合法登记历史通过 :79–82 使 package/mcase.py:180–202 进入工作记录 build（:90 执行防丢检查）。不据此宣称所有孤立/损坏状态均覆盖，本轮未测试。
- working_records_archive/service.py:167–182 仅恢复已支持记录/历史索引/产物，没有恢复音频初始行、人工修订和采样基准的产品实现；:185–192 及 evidence_intake/router.py:91–95 拒绝将历史回执作为活跃授权。
- package_intake/router.py:188–216 在事务中导入、保存 IntakeReceipt/flush、目录 rename，随后 session() 退出提交；异常可删除发布目录。文件和数据库不是同一原子资源，真实中断/提交未知未验。已有 IntakeReceipt 不等于完整恢复就绪协议。
- 因而历史音频时基没有产品恢复往返信任证明。范围函数仅可接收已确立来源的原生保存快照；研究成员、手工恢复行或仅有摘要的历史不能自动变成可播放旧版本。

## 最小接入与验收顺序（仅建议，不是解除暂停许可）

1. 先明确服务器持久报告句级绑定：case/evidence/run/revision/segment/旧摘要与报告版本、审计对应。不可由客户端重传代替；旧报告缺项不可定位，不补造历史。
2. 候选接入点应是报告服务内部解析函数：按案取回可信绑定之后、返回范围之前；同一个新 Session 首读前建立事务，履行报告和媒体两套既有授权及来源核验，把同一 Session 交 ScopedMediaReader。不要用 sources.build_sections 全案扫描替代。文件读取校验的隔离条件需先解决；纯范围函数仍不读文件。
3. 有获准且可证明隔离的新环境后，先锁定依赖、限定无 seed 源码、新建合成库/目录及生成 WAV，再做正常 ORM 精确旧版本/未知范围路径，记录连接/事务与一次读取顺序。当前启动/ORM暂停不因文档解除。
4. 多会话可见性、政策/源变化、权限拒绝、提交失败属于另外的受限前置。须后续明确授权与隔离方案，不能在本轮擅自运行；未证明前不开放路由或页面。
5. 最后验正常保存→报告绑定→导出→重开旧报告→显式授权媒体获取/人工选段。未知不定位，文件内毫秒和事故时钟分开。恢复信任单独验，不以原生正常链代替媒体归档恢复。

仅文档增量，不改运行逻辑、权限、main、mcis-3d 或部署。前一次写文档工具连接中断，经只读确认未产生文件后重新写入；无测试执行。

# 合成试用基础存储初始化（未接工厂）

基线 `983d1b582027038a24d7f692bf4c8e9441ee021f`。仅新增
`common/pilot_core_storage.py::_initialize_pilot_core_storage(db)`，供后续受信装配使用。
不调用全量 `Database.create_all`、models_registry、main 或 launcher；不改默认路径。

## 实际初始化范围

| 真实模型 / 表 | 已核对的必要调用点 |
|---|---|
| CaseRow / cases | pilot_case_discovery → cases.service.load_case；evidence_intake.router.authorize |
| EvidenceRow / evidence_items | evidence_intake.router.load_receipt、登记、evidence.load_item |
| CustodyEventRow / custody_events | load_receipt 的 Register/保管链一致性；evidence.append_custody |
| AuditEventRow / audit_events | 图音追加修订、audit.service.append |
| AccessPolicyRow / access_policies | redaction.gateway.get_policy、reports.access.require_content |
| ArchiveImportHistoryRow / archive_import_history | history_lookup.archived_evidence → 历史命中先 require_content 再原 409 |

依赖证据为上述基线受管源码；`evidence_intake/router.py:90` 的 load_receipt
仍核对真实文件/登记绑定，未改成仅查表。下载 `router.py:236` 的
`attachment_access.protect_container` 对 ZIP 调用 require_content，只需 AccessPolicyRow，
不据此开放报告或归档入口。这里不插入策略、案件、回执或任何假记录。

导入模型不等于建全部表：cases.models 同时注册 vessels/track_points；归档 models
同时注册 archived_manual_interview_receipts/archive_historical_artifacts。
初始化只传六个真实 `__table__`，不遍历 global registry 建表；原归档表 after_create
listener 随真实 Table 保留。审计/保管链四条 trigger 直接复用 Database 原私有实现。
返回前检查六表集合与六条 trigger 的表名/定义。新外键、缺模型、已有表、缺表或缺保护均报错。
仅支持受信调用者新建并独占的合成 SQLite DB；检查不防并发、不证明隔离。
DDL 失败可能部分完成，不承诺原子性或恢复，必须丢弃临时 DB，不能自动重试。

## 明确未闭合，未装配

这不是完整图音初始化成功证明。`image_review/app.py:138`、
`audio_review/app.py:166` 使用各自 Storage，原媒体表和 trigger 尚由原注册管理。
原 `_register_*_review_only` 保持不变，不能用本六表函数替代它们。
`image_review/app.py:106,126` / `audio_review/app.py:78` 对 task-backed 记录
动态导入 tasks.verify_task_binding；其查询依赖 image_ocr_tasks / audio_asr_tasks，
相关模块还导入转换器。当前不创建这些任务表、不绕过或捕获该核验、不开放任务来源。
**不能把缺任务表造成的 SQL 异常冒充既有“无任务”业务拒绝。**
下一步必须先确定限定工厂如何保留真实 task binding 读取/缺失拒绝（窄化任务模型与
只读核验依赖），再显式初始化媒体表并验证最终路由白名单；本次没有声称这已完成。
授权会话、文件根、同源页面、首次登记/保存/重开仍需独立许可与隔离运行验收。

## 本轮实际检查

```
python -I tests_acceptance/pilot-core-storage/check.py
```

9 组标准库 unittest：真实模型表名静态核对、显式 tables 白名单和顺序；
缺模型、外键变更、非空目录对应的假数据库表集合、缺建表、缺/变更 trigger、
创建异常传播。执行的是 AST 去导入后的新函数，metadata/engine/inspect 全为手写替身；
原 Database trigger 方法与归档 DDL listener 循环从固定基线抽取，只交假对象执行。
未导入 SQLAlchemy/FastAPI/应用，未执行数据库/ORM/HTTP/权限/归档/模型测试。
这不是实际 SQLite DDL、catalog SQL 格式、真实权限或启动验收；真实运行可能仍拒绝，
需后续获准后验证，不能据本结果解除暂停。

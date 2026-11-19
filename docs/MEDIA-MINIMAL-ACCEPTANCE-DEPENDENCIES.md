# 图音最小验收依赖表：固定源码审计，不是启动许可

源码固定于 `760b75dfbd621086703b92dd6b195242eb1ba0c3`，分支 `candidate/media-demo-lazy-factory`。本表不包含其他候选的精确媒体引用、报告冻结快照解析或来源策略实现。只读源码；没有执行入口、HTTP、ORM、权限或恢复测试。**目前不能完成“核对→冻结报告引用→导出→重开旧引用”的运行验收。**

[固定源码树](https://github.com/mark2wen2023/MCIS/tree/760b75dfbd621086703b92dd6b195242eb1ba0c3/service/mcis_service)。

下列位置均相对 `service/mcis_service/`，行号针对固定头。C=源码直接确认，D=条件/动态依赖，U=尚未闭合；C 不表示实跑通过。表只界定目标调用链，不是完整最小数据库或可信认证证明。

## 入口 → handler → 状态与守门

|目标/状态|入口与准确符号|读写表/文件及必须保留的控制|
|---|---|---|
|基础案件 C|`cases/basic_registration.py:15` `_register_basic_cases`；GET/POST `/api/v1/cases`、GET `/api/v1/cases/{case_id}`|`cases`；创建检查契约/调查员角色/重复编号，写案件及 `audit_events`。读列表/单案没有同等独立权限门控，不能由“建案有角色检查”推断读隔离。仍依赖 cases.service/models、audit、contracts。|
|凭据预览/登记 C|`evidence_intake/router.py:24` authorize；145 preview_input、154 commit_input|检查同案存在、案号格式、evidence_meta、testimony及Restricted可见性；写 `evidence_items`、`custody_events`，保管事件还关联审计。Register绑定 case/operator/role/摘要；文件为 blob_dir 下 raw/evidence-intakes/.../source.bin，排他写、fsync；失败清理不等于文件/DB跨资源原子。不得提供绕过 preview/receipt 的写入捷径。|
|凭据/原件读取 C/D|`evidence_intake/router.py:90` load_receipt、188 receipt_input、197 receipt_evidence、221 download（以符号为准）|先 `working_records_archive/history_lookup.py:7` archived_evidence 查询 `archive_import_history`，历史命中先 reports.access.require_content 再原历史409；普通分支核对Evidence/Register唯一性、原字节、保管链及绑定。下载另检查 protect_container，追加Access保管事件；不是无副作用读取。不可删历史查询或访问策略。|
|图片导入已有结果 C|`image_review/app.py:59` register；POST `/api/v1/cases/{case_id}/image-reviews`|四凭据 pdf/image/candidate/raw，经load_receipt读取；parse候选及摘要比较，写 `image_ocr_review_records` revision0及审计。只证明所供字节关联，不证明PDF页图血缘或OCR真实运行。|
|图片查看/核对 C/D|同文件89 list_runs、98 read、110 review|列表明确未核验来源；详情及修订核对回执，按case/run取记录；expectedRevision冲突检查、lineIndex范围，追加修订和audit_events，不覆盖原件。initial含artifactTaskId时调用tasks.verify_task_binding，故不是仅修订表的闭包。|
|音频关联/查看 C/D|`audio_review/app.py:33` receipt、39 source、73 check、97 source_context、104 attach、126 listing、132 get|已有凭据对应PCM WAV解析，实际字节摘要、sampleRateHz/frames及机器草稿v2/v3来源比较；写 `audio_review_revisions` revision0及审计。列表不核验来源；详情重新检查原音及草稿。artifactTaskId分支依赖任务记录。|
|音频人工修订 C|`audio_review/app.py:137` revise；POST `.../audio-reviews/{run_id}/revisions`|按case/run读，expectedRevision、segmentId、文本/状态校验；双null保持未知，否则整数毫秒满足范围和实际采样时基。追加修订与审计；时间仅operator_declared，非事故时钟，factVerified仍false。|
|报告当前态保存/读取 C，媒体绑定U|`reports/router.py:29` check_access；73 create_report、91 get_report、101 regenerate、110 review；`reports/service.py:53,96,172`|`investigation_reports`及`report_operation_snapshots`、audit_events；require_content→案件/可用性→调查员→report_draft，创建/复核有WRITE_LOCK和会话。**报告模块本头仍有种子依赖，不可执行。**|
|普通报告导出 C/D|`reports/router.py:138` export_report|权限后读当前报告，调用exporter，再append_operation，写审计/操作快照；GET导出非无副作用。只是当前报告文档导出，不代表固定旧媒体引用。渲染器及外部资源闭包未在本轮审核。|
|报告输出包 C/D/U|`report_output/router.py:109` gate、119 snapshot、218 generate|gate核对Evidence/Interview行身份及full_access；先取报告/策略指纹，释放会话渲染，第二会话重查指纹后写导出审计与快照。不是从头到尾的单一数据库视图；未覆盖媒体精确修订及原件时基的一致读取。依赖Evidence/Interview/AccessPolicy及全量归档service，不能用于证明最小图音闭包。manifest明确client-download-only及stored-report-document-not-source-originals；不是服务端持久绑定或原件归档。|
|授权查看/重开 U|`reports/router.py:91` get_report、130 get_snapshot；`reports/service.py:240` get_snapshot|当前报告GET按case/report key读取；RA快照GET还要求audit权限。二者均未提供“冻结句子→精确媒体修订/片段→当下权限交集”的端点，不可将已有链接当作这个能力。|

## 报告持久历史的准确阻断点

1. `reports/sources.py:157–161` `_citation`仅返回kind/id/href/registration/sourceRef/needsReview等；`build_sections:196`从当前全案证据台账取条目，`ev_citation:200–215`生成通用证据链接。此路径没有保存图音run/revision/segment和人工修订摘要。
2. `reports/service.py:96–126`生成新reportId、family/version，并把完整生成报告作为RA afterValue；但`review_section:172–223`会更新同一ReportRow，整节修改还可将句子集合替换为sectionId-investigator。**reportId/version本身不足以区分该报告之后所有复核状态**。
3. `append_operation:79–92`保存before/after及auditSeq；复核调用传入的是句/节局部值（214–223），不是每次完整报告。`get_report:53–57`返回当前行；`get_snapshot:240–244`只是取指定快照。不能假设可以自动重放任意旧报告。
4. 本头没有接入其他分支的精确媒体reader或冻结生成句解析。最小未来合同应限定一次完整生成RA +其审计身份+句锚点，并持久固定媒体精确版本/片段/摘要；旧无绑定保持未知，不猜latest。合同与事务/授权方案未实现，不能靠测试手造绑定宣称产品闭环。
5. `reports/service.py:13`仍直接导入案件seed模块标识；`reports/sources.py:18,43–46`仍经analysis.router/load_seed读种子，431行以后还有public_text条件路径。本轮只定位代码，不打开种子或原文，不运行生成。图音候选与来源隔离候选不能混称已整合。

## 不可删的保护；不能缩成表名列表的原因

- `db.py:34,53–67`：默认全models_registry/create_all，audit_events/custody_events UPDATE/DELETE触发器；`session:69–79`正常退出commit、异常rollback。WRITE_LOCK仅进程内锁，不能推断跨进程所有权/快照或文件原子性。
- `working_records_archive/models.py:12–18,27–32`：archive_import_history及after_create只追加保护；窄history_lookup仍加载既有模型，不是零ORM导入。
- `image_review/app.py:137–163`、`audio_review/app.py:165–186`：修订表触发器保留，默认register无条件加载并挂任务router。image_ocr_tasks、audio_asr_tasks及音频generation/observation是当前注册/条件核验表面；“不开模型”不等于这些依赖已不存在。
- `reports/access.py:15–23,30–62`：SQLite begin可能BEGIN IMMEDIATE，检查AccessPolicy/完整内容；`evidence_intake.authorize`也查询access_policies。报告业务可延期，但该访问守门不可整体删除。
- `common/context.py:get_ctx`仍从请求头取角色和操作者，并有默认角色；这不是可信生产认证。必须先明确隔离测试的身份供应方式，不注入更高权限规避拒绝。
- `cases/basic_registration.py`避开概览router，但案件service/models仍加载Vessel/TrackPoint类；common.contracts.registry首次校验会扫描schema目录。模块导入下限、实际查询下限、初始化表集合须分别核对。

## 第一轮排除与验收顺序（前置满足并再次授权后才执行）

当前没有启动许可；以下是可验收条件，不是本轮实跑记录。

1. **隔离与装配前置**：固定源码/依赖/完整文件白名单，物理不包含案件材料、种子和凭据；原checkout/用户目录不得成为隐式来源。准备全新私有临时DB/blob目录；空目录预检与venv都不是隔离证明。确认基础案件注册元数据、媒体路由集合和触发器安装，审清动态任务/归档依赖后才允许构造入口。现main/launcher不满足这一条件。
2. **限定第一轮为保存重读**：只使用手造案件、合成PDF/页图/文本结果及非人声WAV/已有草稿；首次原件登记→查询凭据→图音导入→修订→重读，按case/evidence/run/revision核对字节与采样时基。不得声称OCR/ASR执行或核对等于事实确认。
3. **显式排除**：模型任务创建/执行及产物下载入口、归档打包/导入/恢复/历史激活、完整报告生成与导出/输出包。保留历史拒绝查询、访问检查和审计。当前register会挂任务，必须先解决有限装配而不是用“不会点击”代替排除；不能删掉任务绑定核验来接收不受支持记录。
4. **报告独立门槛**：先解决上列冻结绑定、授权交集、同一读取视图及种子依赖，才能在新隔离环境增加“保存固定引用→导出→重开旧句→旧修订”的正常链。旧引用应仍对应旧文本/时间，未知不自动定位；不可用当前报告重读或PDF有链接代替。权限/HTTP/ORM等暂停范围须先获得明确解除，不由本文解除。
5. **停止条件**：出现未列入口/导入/文件访问、原件或记录身份/摘要不一致、历史凭据、unknown提交、权限拒绝、工具阻拦或未确认环境，立即停止相关步骤，不自动重试、不放宽角色/路径/触发器。不得恢复任何既有暂停的权限、故障或归档测试。真实播放器seek/暂停、浏览器、跨进程一致性另行验收。

最短下一步：先只读冻结“基础案件+现有输出导入/修订”的路由/依赖白名单，具体解决register自动挂载任务router的边界；报告步骤保持阻断，不再把本轮表当完整工厂配置。

## 本轮证据与复核方式

仅执行Git固定头读回、白名单源码`git show`/符号定位及文档差异检查；未执行测试或任何业务调用。不新增形式化AST检查器，因为这张依赖表含人工调用链判断，AST通过不能证明闭包。

```bash
git show 760b75dfbd621086703b92dd6b195242eb1ba0c3:service/mcis_service/reports/sources.py
git show 760b75dfbd621086703b92dd6b195242eb1ba0c3:service/mcis_service/reports/service.py
git show 760b75dfbd621086703b92dd6b195242eb1ba0c3:service/mcis_service/evidence_intake/router.py
git diff --check
```

这些命令只读源码，不应扩大为读取seed、样本或原始资料目录。文档后续头不改变上述固定代码基线；本轮没有独立复验、运行隔离或启动通过的结论。

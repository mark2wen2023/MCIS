# 音频转写sidecar v1：隔离数据契约候选

这不是ASR实现。仅纯函数/JSON schema、合成格式fixture、无API/DB/模型/网络。method仅允许manual_transcription，speaker仅unknown，reviewStatus固定pending。未来真正ASR/声源簇/人审发布须另定合同，不能伪填现版本取得“已转写”标签。

validate检查完整键集、来源登记/当前版本摘要、产物摘要、revision/父摘要格式、音频相对毫秒范围、重复ID、已定位与未定位片段、Unicode和大小；允许显式重叠，不把多人同时讲话抹掉。sourceSpan不复用；旧InterviewRecord完全不改。schema.json仅结构，必须另运行validate。JSON schema无法单独检查digest/跨字段时间及整体UTF8字节预算。

compare要求外部给定当前case/evidence/源版本/源状态/产物摘要，缺失unknown，不匹配stale，跨case/evidence拒绝。匹配仅supplied_snapshot_matches_not_authenticated，admissionAllowed/authorizationVerified/asrExecuted均false。

安全边界：传入source和current仍是调用方提供，不是可信DB或SSO。未读取原音bytes，也未证明currentSha真实；登记和当前SHA可不同以兼容保管链Change语义。完整重算hash可自洽伪造，不证明来源或事实。parentArtifactSha仅验证格式，不证明父产物存在、版本连续或未分叉，需后续可信历史服务。旧包不含该sidecar，当前不得接归档写入或静默丢失；未来双端升级前须拒绝含新类型的整包操作。不存在事务写入，因此本轮不能声称生产回滚已测。

可复现：PYTHONPATH=tools/audio_transcript_contract python -m pytest --import-mode=importlib -q tools/audio_transcript_contract。只用合成格式文本，非ASR模型验收，非真实案件资料。包不依赖模型权重，不安装依赖。本候选仅新增tools/audio_transcript_contract内部离线工具目录，无服务导入、路由、DB迁移或归档写入；基于实际main完整父树发布，不导入原隔离仓库历史。

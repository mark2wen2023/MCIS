# 机器草稿 v2：离线研究合同

此增量不是ASR执行器，不安装模型，不读取音频，不接API/DB/归档，不产生人工笔录。
PROFILE MCIS-AUDIO-MACHINE-DRAFT-2 与手工v1分离，旧v1校验器明确拒绝v2。机器method只能machine_asr_draft，reviewStatus固定pending；speaker unknown、相对原音毫秒，继承v1完整源引用和时间范围规则。允许显式未定位片段/重叠。

receipt记录执行ID、provider/model、权重摘要、工具/运行时版本、参数摘要、所声称输入SHA/轨道和输出摘要。输出摘要绑定全部片段、未定位片段和时间基准；外层产物SHA绑定整个包。机器输出或引用改变须同时重算对应摘要，但完整重算仍能伪造，因此不是签名或真实执行证明。inputSha绑定source.currentSha而非原始登记SHA，二者可因保管链版本变化而不同。

origin必须synthetic_contract_fixture或claimed_local_execution，不存在verified选项。inspect永远executionVerified=false/sourceBytesChecked=false/authorizationVerified=false/admissionAllowed=false/humanTranscript=false。completed仅为自报执行结果，本合同只容纳完整草稿，失败/取消/部分输出应在将来的任务回执记录，不能封装为完成草稿。当前字段不记录参数正文/音频字节或凭据。

revision/parent仅格式与初始关系校验，没有可信历史存在性/连续性验证。compare对缺当前快照返回unknown、版本改变stale、跨案拒绝；匹配仅调用方快照一致，非SSO或当前真实权限。

人工改稿必须另立有审核权限、模型原稿引用和人工差异记录的流程；本合同禁止approved/manual_transcription标签，不通过修改机器草稿实现人工审批。尚无此生产流程。任何候选输出应安全文本渲染，字符串校验不构成HTML清洗。

测试全为明示合成格式fixture，非真实模型验收。用户要求的真实模型测试尚须真实授权原音、真实ASR环境与独立听写参照。DeepSeek文本API不能代替ASR。

运行：PYTHONPATH=. python -m pytest -q tools/audio_transcript_contract/test_machine*.py

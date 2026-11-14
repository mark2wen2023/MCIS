# EXPERTCONNECTIONAUDIT 独立复核

12项独立pytest通过（0.08秒），冻结3/3一致。源文件只通过本地固定254167e git对象读取，未执行旧host、测试脚本或请求网络。复跑：
`PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q tests_acceptance/EXPERTCONNECTIONAUDIT/test_independent.py`。

六个公开源文件SHA逐项一致。历史JSONL实际15条连续sequence/相同runId，3 started/3 returned，终态accepted_pending_review且models3/tools2/proposals6/citations6，与审计JSON相符。LIVE_RESULT明确记录实际Pi1.5.2+DeepSeek，但这是历史记录声明，本复核不认证提供方/作者或重新运行。后Skill报告明确7dac为3模拟轮/2工具/1提案、providerRequests=0，旧5d3b不验证新Skill。

旧transport源码行110-111为trust_env=True及cfg.api_key的Bearer头；旧host从stdin apiKey构造配置，scripted_test审读且ready非认证凭证。文档准确区分旧公开损害片段与当前油量两轮专家研究，没有将旧成功推导成当前Vault或占位符机制已接通。

独立负面检查将historicalRecordedRun、currentSafeMetadataObservation、sourceFiles附加当前intent均严格拒绝；合法intent仍blocked且executionAuthorized=false；历史内容作为普通请求消息也无法恢复raw-key，client创建前raw_key_disabled/dispatched=false。历史runId当managed引用仍被production stub拒绝。

当前平台元数据为父协调者记录，本独审未查询API或环境值，不能作独立新鲜度证明；不据其推断用户Vault为空。文档的占位符/可信worker/授权/持久预算路线为条件性计划，不是已实现接口。未发现本审计候选范围内阻断缺陷；当前真实连接仍不可用、HOLD保持。原生浏览器、真实代理、当前模型能力均未验收。

## r1 历史链补充

新增5条参数化只读核验，最终17项通过（0.11秒），r1冻结4/4一致。5份历史JSONL原字节SHA、runId、事件数、实际started次数、终态tools/proposals均匹配historical-chain.json：202d失败3次、be930成功4次、f3ec失败4次、00975成功3次、5d3b成功3次。失败终态无tools/proposals保留null，不补零。historicalLostFourthRunRemainsUnknown=true保留原未知，不据后续成功覆盖；该未知的原始丢失数据无法重新认证。未执行旧host。证据r1-results.txt/r1-hashes.txt；原12项日志保留。

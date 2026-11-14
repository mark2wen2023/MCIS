# 真实DeepSeek适配器提案（尚未实现）

本文件不授权网络调用，不替换3125eaf固定脚本执行器。不得调用旧engine._remote绕过新会议预算/审查。配置中的模型名只是请求字段，未在线核验可用性，不证明后端模型身份。

## 隔离接口

保留Pi子进程无密钥、固定可审计工具；主机提供独立ProviderAdapter接口，接收已规范化且绑定ticket/contextDigest的请求，输出结构化响应或unknown。真实adapter只能显式启用，不因环境变量存在而自动切换。主机通过受支持的安全凭据注入读取凭据，不进子进程、prompt、日志、仓库或回执；不索取聊天密钥。端点/TLS/代理策略须在独审配置中固定，禁止任意URL或通过重定向外泄凭据。

调用前冻结disclosureDigest，覆盖公开packet、所有本次可见完整上一轮未核实意见、系统提示、模型配置、runner版本及预算。摘要变更必须使旧批准失效。来源声明不替代公开性审核；人工答案标签不得进入prompt。没有批准或安全凭据则拒绝真实模式。

## 单一预算账本

所有角色/轮次共用持久化attempt ledger；每回合最多4次提供方尝试和8次工具调用，四回合合计16/32。海青君当前为软件主持，不产生额外模型调用；未来模型主持必须先修订预算合同。120秒回合和600秒会议绝对deadline涵盖等待、提供方请求和退出清理。

发送前原子记录reserved → dispatching；在同一事务保留额度，不能由其他角色重复预支。每个实际重试都要新额度；未知或仍在途请求不自动重试、不退还额度。崩溃恢复时dispatching转unknown并停止；取消不等于提供方未计费。停止新派发、取消支持的请求、终止并回收自己拥有的子进程组，保留局部意见，不补造完成。

请求次数上限不等于货币预算。发送前预留显式max输出token和保守输入token预算；token/金额能力与定价未核验时不得声称硬金额上限。usage缺失标unknown，不写0。重复响应只允许同attempt同digest幂等接受，冲突响应拒绝。

## 可核验回执

版本化新schema，联合绑定meetingId/round/role/ticket、packet/source/prompt/config/context摘要、attemptId、派发状态、响应摘要及进程退出状态。保存提供方返回的requestId、model、usage（如有）并注明observed/unavailable；禁止用Pi占位usage冒充提供方计费。无需落盘原始敏感header，错误日志脱敏。

每attempt状态区分reserved/dispatching/received/validated/unknown/rejected；会议完成须全部必需角色有校验意见且进程退出成功。receiptComplete独立于run状态，导出中途失败不伪造完整manifest。链摘要仅证明本地一致性，不认证作者或提供方身份，不能把声明字段当独立执行证明。

UI同时显示预算预留、实际协议请求、提供方派发/已返回/未知、工具次数、usage可用性；不能把16份预留当16次真实调用。以新schema读取各层，而非重写旧UUID/manifest或把四个回合塞进两个角色数组。保留partial/unknown及分歧，不自动共识、事实、批准或案件写入。

## 验收门槛

先离线验证：并发预算争用、派发前后取消/超时、崩溃恢复、重复及冲突响应、缺usage、provider错误、部分结果、日志脱敏与导出失败。模拟transport只能验协议。再由独立安全审查核对配置/凭据隔离/公开输入；安全注入可用后才有限预算执行一次真实公开案例，并保留实际provider回执。未完成该阶段不可声称真实DeepSeek会议通过。

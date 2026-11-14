> 此文保留1b897f7的v1隔离边界说明。后续显式Pi接通及v2合同见 [PI_INTEGRATION.md](PI_INTEGRATION.md)；旧direct接口仍不自动完成角色。

# 隔离 DeepSeek 提供方边界 v1

基线93284d8；本候选新增真实HTTP传输实现与版本化本地一致性校验，不是已接通的真实Pi会议。未调用真实模型，没有读取安全凭据。禁止用此结果证明专家能力。

## 范围

`transport.request(messages, tools, key=..., deadline=..., cancel=...)` 单次异步POST，固定官方 `https://api.deepseek.com/chat/completions`，模型 `deepseek-v4-pro`，max_tokens2400、stream=false。官方参数参考 https://api-docs.deepseek.com/api/create-chat-completion/ （2026-11-14读取）。TLS默认校验，trust_env=false，不采用环境代理；不重定向、不重试。总截止涵盖连接、响应头与有界响应体；最多262144字节，拒绝压缩。取消会取消并等待自身任务清理。不能保证不合作的替换传输或操作系统故障能被强制终止。

不读取环境密钥、不记录请求/响应正文或异常内容。调用方必须通过受支持的安全注入提供密钥；不应在聊天中提供密钥。低层transport不是案件权限或公开性验证器，只能由审查过的主机控制器调用。

`Adapter(bridge,key=...,enabled=True)` 显式启用；一Bridge只允许一个控制器且要求尚无模型/工具请求，不因环境变量存在自动启用。`dispatch(ticket)` 让Bridge自己构造固定请求，只发送其规范化messages及固定tools，不能外部传入任意案件/答案；每ticket最多4次、整场最多16次，与Bridge共享4/16限制，原工具上限8/32仍由Bridge执行。发送前消耗内存额度，未知/失败不退还；单并发、重复在途拒绝，失败粘性停止。上层必须批准公开材料的完整披露范围后才显式启用。

会话仅在当前进程存活期间有效，不支持恢复或重新导入账本续跑。账本不是持久化发送日志，崩溃后不得按本回执自动重试。额度是请求次数而非货币预算，缺失usage保留unknown；不宣称token或金额硬上限。

Adapter自身120/600秒deadline之外，每50ms以内协作轮询Bridge原有回合/会议截止，避免晚绑定重置原截止。取消调用Bridge.stop；已派发但未可靠返回均保留unknown，不能证明提供方未收到或未计费。非200（包括429与重定向）、错误JSON、响应过大、连接异常均停止，不重复请求。

**接通限制：**返回assistant与提供方metadata给受信主机，但故意不调用Bridge.scripted_response/submit_simulated，也不修改Executor的固定脚本提供方。现有Bridge仍保持在途，不能把真实返回冒充模拟完成。后续需要独立实现真实响应接收路径和Pi执行器集成。本轮测试在mock transport下显式调用脚本续接，仅验证跨轮预算，不能声称端到端真实会议。

## 版本化回执

`receipt()` 只允许非运行中导出；`validate_receipt(bytes)` 拒绝重复键、未知字段、超2MiB、未知版本与篡改。schema=`mcis.public-expert-provider-receipt.v1`；每attempt绑定会议模拟快照、ticket、contextDigest、输入消息摘要、递增请求ID、响应摘要和提供方id/model/usage（可unknown）。快照重放验证、跨attempt事件前缀、4/16次数与哈希链联合验证。未知结果必须末项且halted。该schema是提供方账本，不是完整Pi运行回执或工作台输入。

所有attempt状态为received_unverified / unknown / not_dispatched；无角色完成状态。meetingCompleted与authenticityVerified固定false。摘要验证仅本地一致性，重算链不能认证作者/提供方。原快照simulation_only是结构状态，不是实际提供方执行证据。metadata只是响应中观察值，模型字段不是独立身份认证；mock也能构造同样形状。不能从字段声明推断真实模型执行。

## 公开材料与测试主张

仅使用冻结public-packet：三条人工编写测试主张（含反例），同一报告PDF28/印刷26，不是三份独立证据。主张不等于报告结论；固定报告逐字引用与模型选取引文应分区。未把逐条答案/expectedLabel/goldLabel送模型；packet、提示与旧执行器未修改。来源PDF本轮未重新认证，模型引文精确子串不等于语义正确。显示修订43d9f62属于另一分支，未声称此树已接入工作台。

## 测试

```
PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q research/expert_remote
```

58项离线协议测试，使用httpx MockTransport并禁止socket连接，绝不使用旧_remote。36传输用例+22适配器用例。覆盖重定向/429/错误正文不泄漏、响应长度/压缩/JSON/usage、取消前后/外部取消、deadline、并发拒绝、未知结果停止、16次预算和版本化回执语义篡改。模拟消息和占位密钥只用于测试。真实DeepSeek、Pi远程全程、持久化恢复、原生浏览器、身份/案件权限均未验收；不部署、不合并。

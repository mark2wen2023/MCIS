# raw-key 在线路径默认拒绝（EXPERTRAWKEYHOLD）

基于75b3ef4，按授权禁用专家研究旧在线raw-key入口。真实DeepSeek请求0；不读真实凭据，不改平台网络/安全设置。Personal Vault仍按官方占位符机制等待可信bootstrap，不把环境JSON或ready当证明。

## 拒绝边界

- transport.request 默认无managed绑定且无显式MockTransport时，在HTTP客户端创建前拒绝raw_key_disabled。无enable参数或环境开关。managed与mock互斥；只接受精确httpx.MockTransport类型，不接受其子类、普通网络Transport或布尔开关。
- isolated非mock且无managed引用在启动子进程前拒绝；直接执行worker的raw-key stdin也经transport拒绝，无成功结果且dispatched=false。
- Executor provider_mode=remote在构造时拒绝。Adapter direct/remote兼容对象仍可构造，但默认派发被底层拒绝，预算记录not_dispatched并halt，不能重试。
- 旧CLI --approved-remote在read_secret和创建输出前拒绝；已有批准摘要不能启用。旧engine.run_group非fixture在解析packet前拒绝；_remote只保留明确拒绝stub，删除旧网络实现。
- managed缺可信绑定仍拒绝，不自动选择raw-key回退；mock worker只构造固定合成处理器。

## 保留与兼容风险

明确的offline_transport仅供合成协议测试；实际httpx客户端强制使用该MockTransport，仍固定目标且禁重定向/重试。MockTransport handler是本地Python代码，不是沙箱，不防恶意代码/monkeypatch，也不证明其不会自行联网。测试另行禁止socket连接，绝不提供真实key。`identityVerified=false`不变；模拟成功不能当真实模型验收。

raw-key旧调用及原本允许remote的SDK用法有意中断，拒绝为静态错误；没有兼容性自动降级。scripted/remote_mock与CLI fixture、describe、历史回执verify/display继续保留。未来恢复真实路径必须新审可信平台绑定与配置回执，而非传key或改布尔值。

旧协议测试保持回显/超时/预算/取消断言，fixture改为显式注入MockTransport，不能凭新HOLD提前返回冒充行为通过。旧engine六项在线行为测试按新合同改为零HTTP拒绝；对应超时/重定向/unknown协议行为仍由expert_remote离线测试覆盖。历史冻结文件和旧报告保留历史含义，不代表现在运行代码逐字相同。工作台来源测试中只有engine实现hash因授权禁用而更新；公开packet/manifest、模型提示和Pi runner未改。

75b3ef4独审的精确回显防护继续保留，不覆盖编码变形/分片或程序未知的代理真实key。取消仍按原独占reaper/稳定SIGCHLD约束处理，预算仍16/32、单角色4/8、120/600秒；没有持久化重启额度或货币上限保证。

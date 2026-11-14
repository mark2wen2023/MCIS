# Personal Vault 接线核查：HOLD

2026-11-14，父提交 cafffbd1dcc157be8e87b0187c7aecc5639eee22。本轮只修正文档与补充拒绝路径测试，不接通生产、不改环境设置、不读取凭据值。真实 DeepSeek 请求为 0。

## 官方机制与旧候选的差距

[官方 Cloud environments 文档](https://learn.chatgpt.com/docs/environments/cloud-environments)明确：network secret 向程序交付占位符，代理在允许的 HTTPS:443 目标替换真实值；不同于直接向程序交付值的环境变量。Personal Vault 必须匹配环境请求的 key 和适用环境；仅存入 Vault 不代表任务已绑定。更新发布环境后应在新任务核验。

这纠正了 cafffbd 的假设：proxy_header_injection 不是已核验的平台合同。旧离线正测没有 Authorization，只验证假设，不能证明 Personal Vault 可用。该实验验证器暂保留以保存既有测试证据；生产 platform_binding 仍无条件拒绝。不要把它改成接收环境 JSON、自声明 ready 或根据占位符前缀推断可信类型。

## 本实例的可核验证据

cloud_environment_environment_status 返回 observations_current=true，spec_revision=observed_spec_revision=1，secrets=[]、runtime_variables=[]、outbound_identities=[]，source_config_id/source_config_version_id 均为 null。代理可用或网络 unrestricted 不等于存在 credential binding；上述信息也不能证明用户 Vault 为空。当前工具没有控制面到 Python worker 的认证 bootstrap；工具响应不会自动变成 worker 的可信来源。未读取诊断日志、密钥或代理变量值。

旧 raw-key transport/Executor 路径仍存在，本 HOLD 不是全局网络封锁。此次不执行该路径、不读取 DEEPSEEK_API_KEY，也不把它当作 managed 失败后的回退。

## 必须先解决的三个前置

1. 在平台设置中由有权限者核对 Network secret 类型、环境请求的 key、Personal Vault 适用范围及 api.deepseek.com 目的域。通过受支持配置流程发布并在新任务确认绑定；本轮不代改设置、不要求聊天粘贴值。
2. 平台需提供程序可验证的可信配置交付方式：绑定当前实例/版本、来源类型、目标范围、新鲜度/撤销；父进程与 worker 均可验证，且不能由模型可写文件或环境自声明替代。当前未找到该能力，不能杜撰平台签名/API，也不能把 source_config 非空单独当证明。
3. 只有前两项成立后才改传输与 Executor：占位符仅交固定 provider worker 构造 Authorization，不进入 Pi/model 消息、日志或回执；实际密钥由平台代理替换。固定 DeepSeek HTTPS:443 POST、TLS 验证、无重定向/重试、不回退直连。回执绑定无秘密的配置引用/版本及尝试、预算、取消/unknown；引用和摘要本身不是身份认证或实际模型调用证明。

接通后仍须独审和一次有界公开材料验收：同一冻结 packet、最多 2 轮/4 角色任务、16 provider 尝试/32 工具、单任务 120 秒/总 600 秒、每次输出上限 2400。未知结果不退款/重试，不把输入中的人工反例标签泄露给模型。不将预算上限称为货币硬上限。

## 本轮离线测试范围

test_bootstrap_hold.py 用无法读取的合成环境、禁止 HTTP 客户端/子进程创建的哨兵，检查 resolve、transport、isolated、worker；自声明 ready 和 credential 名称存在仍拒绝。不会 monkeypatch 生产 platform_binding 为成功，不向任何服务器发送请求。managed+mock 被拒，失败没有成功回执。此测试不证明真实代理替换、worker bootstrap 或 Executor/回执已接通。

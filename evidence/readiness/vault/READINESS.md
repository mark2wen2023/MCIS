> 历史证据归档（2026-11-14），不是当前授权或可执行说明。未在本次归档重跑原测试/模型；旧raw-key路径已在498f807禁用，真实执行仍HOLD。来源、原始摘要和归档摘要见MANIFEST.json。

# Personal Vault / DeepSeek 安全注入核查

2026-11-14。仅元数据与变量名存在性检查，没有读取、打印或复制任何密钥值，没有服务探测或模型请求。未修改环境配置或仓库。

## 证据与环境边界

- 当前environment_status为observations_current=true，spec_revision/observed_spec_revision均1。secret bindings、outbound identities、runtime variables均为空；source_config_id和source_config_version_id均null。完整非敏感标识见environment-metadata.json。
- 当前environment_id与本开发线此前凭据核查的ID相同。没有另一个“DeepSeek测试环境”的ID/配置版本证据，也没有可用的跨环境列表工具，所以**不能断言与另一个测试环境相同或不同**。项目仓库相同不证明运行环境相同；source_config=null亦不证明用户Vault为空。
- 当前网络策略元数据为unrestricted/enforced；没有证据说明api.deepseek.com被域许可拒绝。阻断是未绑定凭据及适配器代理兼容性，不能因此盲目扩大网络权限。
- 当前进程仅检查变量名：DEEPSEEK_API_KEY不存在；HTTP_PROXY/HTTPS_PROXY及小写、NO_PROXY及小写、SSL_CERT_FILE、REQUESTS_CA_BUNDLE存在。未读取它们的值、未访问凭据文件；具体布尔结果见process-presence.json。
- 未查询Personal Vault条目内容、秘密值、诊断日志或其他Site的生产变量。无Vault枚举工具，空环境绑定只能证明此实例未绑定，不能证明Vault没有用户已保存的DeepSeek条目。

## 受支持的注入方式及当前不兼容点

依据已读取的Cloud Environment运行技能networking/environment-changes参考：平台可经HTTPS代理在匹配路由注入网络凭据或替换占位值，匹配范围含scheme/host/port/method/path。网络许可与凭据绑定是两项独立配置；绑定需state=ready且当前observed revision一致，才可视为配置就绪。平台要求保留所提供代理变量及CA信任，不能用绕代理、清空代理、关闭TLS校验来“验证”密钥。

现有transport.py使用httpx trust_env=False，isolated.py向worker只传PATH/LANG；因此代理和CA设置未被保留。Adapter还要求显式key。即使用户在Vault已有网络密钥，此路径也**不能直接认为已使用平台代理注入**。本轮不试探api.deepseek.com、不尝试占位token、不访问余额或models端点。

当前工具仅提供environment_status及诊断读取，没有request_changes或Vault条目绑定工具。不能由本代理完成绑定变更；诊断可能含秘密，此任务不需要读取。

## 可执行解决步骤（不在聊天重发密钥）

1. 协调者/用户在当前Codex聊天的运行环境设置（若界面提供）确认environment-metadata.json中的实例ID；同时在原DeepSeek测试环境查看其环境ID、source配置ID/版本。只比较这些非秘密元数据，不复制秘密或把“同仓库”当“同环境”。若设置界面不支持当前实例绑定，则用已有正确环境配置启动新任务，并重新核验环境ID/版本。
2. 在该实例设置中**选择已有Personal Vault引用**，不要重新粘贴到聊天、仓库或命令行。明确限定https://api.deepseek.com:443、POST /chat/completions及必要域许可；采用设置界面实际支持的映射/网络凭据类型，不猜Vault字段。若不存在该引用，只在Vault设置内管理，不能通过聊天传值。
3. 保存仅作用当前实例的配置后重新读取environment_status，确认observations_current、observed revision匹配、所选绑定state=ready和目标策略已生效。其他已运行任务不会自动获得同一配置；若需要未来任务复用，使用设置提供的Promote/发布流程并在新任务复核，不能据此假定当前实例已更新。
4. **先做代码适配与离线审查，不能直接开模型：**新增显式“managed proxy”路径，保留平台提供的代理/NO_PROXY/CA变量到固定worker，保持TLS验证、禁止重定向重试及同一16次账本。网络身份绑定无本地key时应有独立明示模式，不应使用伪造key去通过旧构造器；若绑定提供占位变量，须按实际元数据/官方契约接入，不能把占位符当实际密钥证明。不要只把trust_env改true就宣布完成，应分别验证worker净化白名单、目标路由、头部日志脱敏和取消/未知语义。当前未实现这项适配。
5. 先用MockTransport/受支持代理替身做离线协议验收，确认不读取/落盘真实秘密，不扩大目标和方法。协调审查通过、绑定ready且公开材料与预算重新冻结后，才进入单次真实验收。平台策略拒绝时停止；不能改直连、关闭TLS或绕审批。

## 单次公开案例验收准备

single-run-plan.json绑定4dda486和31个当前实现/公开包文件摘要；这是待适配前的冻结基准，不是最终可执行许可。代理模式代码或环境配置变化后必须重新冻结并复审，不能复用旧摘要放行。

计划仅一场两轮/两个软件角色/四席：每席最多4次请求、8次工具、120秒；全场16次请求、32次工具、600秒。每次max_tokens2400，总输出预留38400不是实际usage或货币硬上限。没有自动重试或失败后换模式/模型；未知、取消、截止、所有权丢失、回执失败即停止且保留部分结果。内存账本不支持崩溃后自动续跑。

材料保持公开YANGZE22冻结片段，三条人工编写测试主张（含反例），同报告同页；固定报告引文与模型选取引文分开。逐条人工答案/反例判定不进模型提示。第二轮只读完整上一轮未核实意见；动态生成内容在每轮contextDigest和每请求inputDigest里绑定，不能提前伪装冻结。

保留schema2复合回执、provider v2账本、每次请求/响应ID及摘要、usage observed/unknown、Pi/worker退出回收、预算与完整性；用独立validator校验并保管原件字节SHA。模式声明/哈希不是独立真实调用或模型身份认证。模型质量需另对真实输出人工评审，MockHTTP不得替代。

当前结论：**安全注入未绑定、现有worker不兼容已提供的代理环境，4dda486协调独审尚未提供结论，真实验收暂停。真实DeepSeek请求0。** 不需要用户在聊天重发密钥；不部署、不合并、不自动修改配置。

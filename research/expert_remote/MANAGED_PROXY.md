# 平台安全网络密钥代理：离线最小候选

> 2026-11-14 官方机制核查更正：下文“代理补 Authorization”是假设，不能视为平台支持。实际文档描述占位符替换；生产继续拒绝。以 [VAULT_BOOTSTRAP_HOLD.md](VAULT_BOOTSTRAP_HOLD.md) 的阻断说明为准。旧 raw-key 路径仍存在，不是全局禁止直连。

基线4dda486；不修改平台网络/安全配置，不读取真实密钥或环境变量值，不调用真实服务。当前实例没有安全绑定/配置引用。**生产读取器platform_binding始终拒绝，真实请求HOLD。** 本文件的normalised schema是MCIS待审合同，不是已存在的平台API，也不是平台签名/身份验证。

## 已实现的有限边界

复用原transport、isolated、worker，新增可选managed_binding引用。调用者不能传代理URL、CA或任意配置文件。resolve先要求可信platform_binding，成功后才读取白名单环境；缺引用/无bootstrap在创建HTTP客户端或worker前拒绝。当前没有可信控制面到进程/worker的桥，不能把环境JSON、人工ready或测试替身换成生产证明。只有后续独立审查的真实平台读取器才可补齐此接口。

离线验证器要求环境ID与运行实例一致、source配置ID/版本、observed revision一致、current/ready/未撤销、未来不超过1小时的有效期；目标仅https://api.deepseek.com:443/chat/completions、POST、代理注入Authorization。字段与结构严格限定。所有元数据真实性依赖未来可信bootstrap；本校验器本身不能认证它们。

允许变量名仅HTTP_PROXY/HTTPS_PROXY及小写、NO_PROXY及小写、SSL_CERT_FILE、REQUESTS_CA_BUNDLE，存在集合和每项值摘要必须与批准快照完全一致；大小写/HTTP与HTTPS代理冲突拒绝。拒绝ALL_PROXY等隐式替代配置。proxy需明确端口，限定http/https、无userinfo/query/fragment/额外路径/控制字符；缺代理、错摘要、被NO_PROXY匹配目标时停止，不修改用户配置来放行。

CA为有界普通文件，逐层O_NOFOLLOW拒绝符号链接/非regular，摘要验证后使用**同一份已读取字节**构造SSLContext，拒绝私钥文本。httpx保留trust_env=False，显式传入校验后的proxy和verify context；HTTPS代理与目标TLS均使用该验证context，hostname检查保持开启。NO_PROXY保留传给worker但不控制显式固定目标的路由；不会因此回退直连。平台提供不兼容配置时应另审，不自行清除或修改。

本候选只支持待确认的“代理增加Authorization头”合同，应用不构造Authorization、不接收raw key；key与managed_binding同时提供拒绝。平台实际若要求占位变量替换，须按ready绑定的真实契约另行适配，不能猜占位符或把假key当成功。未验证真实Personal Vault注入/CONNECT/代理证书路径。

仅固定提供方worker可继承已验证网络白名单，Pi仍原净化环境。worker重新resolve同一引用；managed与--mock互斥。当前bootstrap缺失，受控子进程链实际仍会拒绝managed启用；离线正测只以受控替身验证transport参数与HTTP协议，不能宣称已完成平台端到端运行。

## 尚待绑定后的接线

现有Executor/Adapter未自动选择managed路径。生产bootstrap和worker可信引用传递方案未实现，默认拒绝是刻意门禁。未来需绑定实际环境配置引用并复核控制面新鲜度/撤销；确定平台注入究竟是头部增加还是占位替换后，再把Executor参数和版本化回执（绑定引用/配置摘要）接入，重冻单次预算和披露。不得通过删stub、trust_env=True、手填ready或任意代理来假装已就绪。

设置可用时，在正确实例环境设置选择已有Personal Vault引用并保存，重新确认metadata ready；不要在聊天重发密钥。当前无request_changes工具且本任务仅研究实现，没有更改设置。所有权6f8f429的独占reaper/稳定SIGCHLD约束保持，模型预算4/16与工具8/32、deadline、unknown停止不变；本候选不新增重试、绕过或模型调用入口。

## 离线证据

新增42测试：默认无bootstrap先拒、精确pins/TLS、错误ready/环境/版本/过期/撤销/目标/注入类型、任意代理/冲突变量、CA替换/链接/目录、检查后更换CA使用原验证字节、代理userinfo/query/fragment等拒绝、目标NO_PROXY拒绝、显式proxy/context且无应用Authorization、301/302/307/401/429/503单次失败无回退、不泄露代理/CA到错误栈。使用公开ISRG根证书和MockTransport；未读取真实代理/CA环境值、未用真实Vault绑定或密钥。

运行：`PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q research/expert_remote/test_managed.py`。

测试不证明真实网络注入成功，也不把mock结果标真实。独立安全审查和未来有绑定环境的验证均是额外门禁；不合并、不部署。

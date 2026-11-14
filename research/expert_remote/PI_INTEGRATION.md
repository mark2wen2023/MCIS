# 实际 Pi / 隔离提供方接通候选

基线1b897f7。默认Executor仍scripted；真实模式只能显式组合：`Meeting(provider_mode='remote')`、`Bridge(meeting)`、`Executor(bridge, provider_mode='remote', key=安全注入值)`。这段API说明不授权执行；本轮没有读取凭据或调用真实DeepSeek。`remote_mock`是单独显式模式，使用固定MockTransport，顶层和逐次回执保留transportMocked=true、realDeepSeekExecuted=false，不能当能力验收。

## 同一完成路径

实际Pi1.5.2进程及固定runner不变，沿原Executor的管道、工具验证、done、exit0、组清理与父接受门禁。remote模型请求由Bridge一次预留，Adapter只接受与pending_request完全一致的请求，不二次扣数。每回合4/8、两轮16/32边界共享；旧_remote没有参与，没有绕过Executor。第二轮两角色只见同一份完整上一轮意见；同轮意见不进入对方上下文。

Bridge.provider_response与scripted_response互斥，remote成功通过submit_provider_response提交，绝不调用submit_simulated。Meeting协议状态用schema2/remote_protocol_declared；状态声明不是模型身份或实际调用证明，realModel/realPi协议字段仍不作运行观察。真正的Pi进程和提供方请求由复合回执另层记录，不能把模拟层字段改成真实。

## 超时、取消、凭据

每次提供方请求在固定Python worker中调用1b897f7 transport，固定官方HTTPS端点、TLS校验、不重定向重试。worker使用净化环境和新进程组，密钥只经有界stdin传入，不进命令行、Pi进程或回执。显式mock worker仅替换HTTP传输，生产remote无该替换。

父进程每约10ms检查取消/绝对deadline及Bridge原回合/会议截止；不依赖worker合作式退出。超时/取消SIGKILL自己拥有的worker进程组并wait回收，再由原Executor清理Pi组。正常worker退出也先清组再回收，避免PID复用。进程回收等待上限5秒；这是本地进程监管，不是OS安全沙箱或取消提供方计费的保证。错误/无响应视为unknown，不自动重试、不退预算、不补完成；未知请求即使后来在提供方成功也不会自动写入意见。

## 回执

提供方账本v2增加transportMode与每次worker启动/退出/回收/mock标记；保留v1读取。输入消息摘要、ticket/context、重放快照、请求序号、响应摘要和usage可用性继续绑定。会议信息不自动变成事实；人工测试主张（含反例）与报告逐字引用口径不变，未添加逐条答案标签或改packet。

Executor远程复合回执schema2含providerReceipt、Bridge预算和Meeting快照及Pi运行事件；成功角色要求对应请求全部received_unverified、工具验证、COMPLETED候选、Pi退出0且回收。收到HTTP响应不等于完成角色。realDeepSeekExecuted仅remote模式的本地成功响应观察，不认证服务器身份、模型型号或语义质量；MockHTTP路径固定false。哈希与声明可被伪造，校验只证明本地记录一致性，不能独立证明真实调用。

当前内存账本不支持崩溃恢复/断点重试，不能当持久化发送日志。请求数不是货币硬预算。工作台仍没有多轮回执UI，本候选不宣称浏览器接通；生产身份、案件权限及正式案件均不在范围。

## 本轮实际验证

安全协议测试使用公开冻结packet、显式MockHTTP及合成占位凭据。实际4个Pi进程、12个worker完成两轮，上一轮意见数量0/0/2/2；默认旧脚本流程继续回归。另用不合作的睡眠worker证明硬截止和取消回收，保留未知请求。没有真实DeepSeek、没有模型质量验收，没有部署合并。真实验收仍须可用安全凭据、独立审查和有限公开案例运行。

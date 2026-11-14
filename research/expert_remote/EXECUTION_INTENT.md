# 浏览器到执行器：离线准备接口（EXPERTINTENT）

基线498f807。此候选不提供真实执行API、身份认证或可信凭据注入；真实请求0。当前平台只提供assistant侧安全环境状态查询，未发现可由worker验证的bootstrap或配置变更工具。最近安全元数据仍为无secret/runtime变量绑定、无source config引用；未读值、日志或密钥。环境可联网不等于凭据就绪。

[官方云环境文档](https://learn.chatgpt.com/docs/environments/cloud-environments)描述Network secret向程序交付占位符，在获准HTTPS:443目标经代理替换。Personal Vault的key与适用环境须匹配环境请求。文档并未为本仓库提供worker可验证bootstrap；工具返回元数据不能自动成为Python信任根。不得用浏览器ready、环境JSON或人工引用替代。

## 当前缺口

| 边界 | 已有 | 未实现，保持拒绝 |
| --- | --- | --- |
| 浏览器 | 固定公开材料只读视图、显式导出准备请求 | 认证会话、服务端授权、CSRF/来源边界、任务提交接口 |
| 执行器 | 有界会议、Pi MockHTTP协议、raw-key在线默认拒绝 | 经可信平台绑定的managed执行路径 |
| 凭据 | 占位符机制文档、默认拒绝stub | 当前实例可信绑定与worker交付/撤销/新鲜度验证 |
| 预算与取消 | 单进程会议预算/取消及进程清理 | 服务端原子预留、持久幂等、重启恢复、经授权取消 |
| 审计 | 本地回执链一致性与只读展示 | 身份/授权/配置绑定/intent到实际回执的可信关联 |

## 最小合同

现有工作台“导出运行准备请求（不执行）”生成 `mcis.public-expert-execution-intent.v1` JSON：只有schema、UUIDv4 intentId、固定operation、冻结packetSha256。不得携带key、proxy、endpoint、ready、budget、caseId、sourceText或当前意见。UUID仅用于关联，不是身份、批准或幂等锁。同页重复导出复用相同内容；刷新可产生新ID，没有服务端去重承诺。浏览器下载动作不等于用户已保存，页面据实显示未确认保存。

`python -m research.expert_remote.preflight --check-stdin < mcis-public-expert-intent.json`

最多读取4097字节，超过4096拒绝；严格键集合、重复JSON键、非有限值、UTF8和固定来源检查。合法输入的canonical摘要用于对照内容，不认证作者。预检是纯函数，CLI永远退出2：合法为blocked，异常为invalid。输出明确executionAuthorized/requestDispatched/authenticityVerified/isExecutionReceipt/limitsReserved均false。proposedLimits只是未来固定预算建议，不是实际额度预留。预检不导入Executor、读取环境、持久化、联网或重新运行模型，也不因某次平台状态改变自动放行。

缺凭据时这不是提交入口的替代品；未来受信服务必须重新校验并独立授权，不能接受这份预检输出作为授权。必须先补认证/可信绑定/原子预算与幂等/取消/审计，然后才设计执行接口，另行独审。模型输入仍固定公开材料，不携带人工反例答案标签。

## 验证与限制

26项Python预检测试，DOM准备请求两次下载内容一致、失败脱敏/缺crypto拒绝、TS→Python合同验证。既有会议状态/来源/导出回归保持；测试仅合成DOM/MockHTTP。没有建立监听或API，没有平台配置变更、真实凭据或真实请求。此环境既往Playwright在导航前因SUID沙箱配置失败；本轮无配置变化，不重复绕过，原生下载、布局/键盘与CSP仍未验。浏览器下载由DOM测试截获，不声称实盘保存。

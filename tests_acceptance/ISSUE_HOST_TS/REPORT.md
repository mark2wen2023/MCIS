# Issue host TS bridge 独立审查

## 审查发现

1. 初稿使用 {...command} 转发全部字段，实际独立测试证明额外token字段进入send callback（虚构SECRET字符串，非真实凭据）。实现者已改为请求/entry严格键白名单。
2. 初稿await后使用调用方原command.caseId/issueId，静态审查发现可变引用风险；实现者改为最早structuredClone并全程使用冻结副本。独立测试对调用方修改及host修改均检查。
3. 初稿contextId正则接受36个连字符；改为规范UUID格式。
4. 第一版白名单修正仍只验证键，独立测试实际证明entry.note中的对象{token:'SECRET'}会进入send；需要entry字段值类型和范围验证。

## 已执行的链路

曾独立运行issue-host-integration.tsx，退出0：真实React/HappyDOM交互，经TS业务port、Node stdio fixturehost、Python受保护ASGI、临时SQLite，五条工作记录及重新读取通过。案件/subject/session由fixturehost可信配置，不是用户浏览器真实IPC、生产登录/IdP、部署、LLM或真实事故数据。

TS独立检查在issue-host-independent.ts；最终结果与冻结hash待修正完成后补充。未修改产品，未推送合并部署。

## 最终结果

entry值类型与范围校验修正后，独立TS15/15通过，退出0；完整React/HappyDOM→stdio→受保护ASGI→临时SQLite链路再次通过，退出0。最终无剩余阻断项。

15项涵盖body额外内容只投影已知字段、requestId/contextId/caseId/profile/productionLogin/ok错配拒绝、跨案调用前拒绝、scope副本隔离、command额外字段send前拒绝、非法UUID、await期间调用方变更、note对象嵌套字段send前拒绝、host异常脱敏、sender修改消息不改变校验目标。

最后hostPort.ts SHA-256：ad9509702797da571d6da154895dc0c8034b8db1d8b029afd8d794de9eb0eae1。

没有把历史失败数量累加为通过覆盖；没有把可信fixturehost等同生产IPC授权。Python桥接实现另有独立审查，本报告不是其全部权限边界的认证。

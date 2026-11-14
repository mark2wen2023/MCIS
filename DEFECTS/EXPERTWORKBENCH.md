# EXPERTWORKBENCH 独立缺陷裁定

## EW-D01：固定执行器状态与计数矛盾被接受（已修复）

发现版本：初始 `logs/EXPERTWORKBENCH-impl-hashes-frozen.txt`，model.ts SHA-256 `511ef01b293e8672bc654f8cd5bafb25351cfb216236c8d436990224bf32d5f8`。

最小复现：`node tests_acceptance/EXPERTWORKBENCH/test_independent.mjs --repro`。初始有效控制用例通过，以下四条拒绝断言失败：not_started 角色含非零计数；完成角色零模型调用；完成角色零工具调用；remote completed 总 modelCalls=6 而 providerRequests=1。

影响：畸形 JSON 可被显示为固定版本可接受的运行状态。不是身份认证或权限绕过；页面本来就不验证真实性，但这些状态与已绑定执行器合同矛盾，不应通过结构校验。

裁定：not_started 的两计数必须为0；完成角色至少2模型/2工具；remote completed 的 providerRequests 必须等于两角色 modelCalls 总和。failed/unknown 保留更少实际请求的合法状态，不能用完成规则误拒绝回执前失败。

实现者 r1 修复，冻结 `logs/EXPERTWORKBENCH-r1-impl-hashes-frozen.txt`。独审保留原始四断言和失败日志，原断言复跑全通过，新增边界断言通过。总计51/51，9/9冻结文件一致。状态：关闭（2026-11-14）。

## 保留的验收边界

原生 Chromium 沙箱启动失败，未绕过；Happy DOM 与静态 CSP 校验不替代真实浏览器验收。未调用真实模型，不认证结果真实性/作者、语义正确性、PDF、回执完整性或正式案件权限。当前离线查看器约定范围无新增未关闭代码阻断；上述项目仍不可声称已验收。

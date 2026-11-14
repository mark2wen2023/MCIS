# EXPERTWORKBENCH 独立缺陷裁定

## EW-D01：固定执行器状态与计数矛盾被接受（已修复）

发现版本：初始 `logs/EXPERTWORKBENCH-impl-hashes-frozen.txt`，model.ts SHA-256 `511ef01b293e8672bc654f8cd5bafb25351cfb216236c8d436990224bf32d5f8`。

最小复现：`node tests_acceptance/EXPERTWORKBENCH/test_independent.mjs --repro`。初始有效控制用例通过，以下四条拒绝断言失败：not_started 角色含非零计数；完成角色零模型调用；完成角色零工具调用；remote completed 总 modelCalls=6 而 providerRequests=1。

影响：畸形 JSON 可被显示为固定版本可接受的运行状态。不是身份认证或权限绕过；页面本来就不验证真实性，但这些状态与已绑定执行器合同矛盾，不应通过结构校验。

裁定：not_started 的两计数必须为0；完成角色至少2模型/2工具；remote completed 的 providerRequests 必须等于两角色 modelCalls 总和。failed/unknown 保留更少实际请求的合法状态，不能用完成规则误拒绝回执前失败。

实现者 r1 修复，冻结 `logs/EXPERTWORKBENCH-r1-impl-hashes-frozen.txt`。独审保留原始四断言和失败日志，原断言复跑全通过，新增边界断言通过。总计51/51，9/9冻结文件一致。状态：关闭（2026-11-14）。

## 保留的验收边界

原生 Chromium 沙箱启动失败，未绕过；Happy DOM 与静态 CSP 校验不替代真实浏览器验收。未调用真实模型，不认证结果真实性/作者、语义正确性、PDF、回执完整性或正式案件权限。当前离线查看器约定范围无新增未关闭代码阻断；上述项目仍不可声称已验收。

## EW-D02：remote partial 已完成角色与提供方响应声明矛盾（已修复）

发现基线：`b2707a49de54ce8cb1053d578c6ae116d766a763`，r1 冻结。父协调审查指出：group not_accepted/unknown，source_attribution completed_unverified（3模型/2工具、完整意见），另一角色未完成，transportMocked=false，但 realModel=false/providerRequests=0 仍被接受。

独审新增6项测试，57项中53通过/4失败，保留 `tests_acceptance/EXPERTWORKBENCH/r2-prefix-results.txt`。三条拒绝失败：零请求/未收到响应、有足够请求但realModel=false、有响应但requests小于已完成角色模型次数；一条DOM失败：此畸形partial取代了此前已载入的模拟结果。

执行器静态语义核验：`research/expert_group/engine.py` 242-251 每个remote模型轮均递增modelCalls，provider_request回执成功后递增providerRequests，_remote返回后realModel=True；282行之后才标角色完成。故任何已完成remote角色均已收到响应，并为其每轮请求留下计数。模型调用计数先于回执，未完成角色允许requests少于modelCalls；发送后响应未知的失败也允许requests>0且realModel=false。

裁定最小修复：remote任一角色完成时realModel必须true，providerRequests至少为所有已完成角色modelCalls之和。不得对所有partial强制请求数等于总轮次。新增合法控制覆盖已完成3轮+未完成1轮仅3请求、无完成角色1未知请求未收到响应。实现与独审均不调用模型或网络。


EW-D02 r2 复验：实现者添加 completedCalls 全部完成角色求和与 remote 响应声明校验。原三模型拒绝和一DOM断言全部转绿；增加两角色已完成但组失败时请求不足拒绝/请求充足允许两个边界。独审59/59通过，r2冻结9/9一致；证据 `tests_acceptance/EXPERTWORKBENCH/r2-results.txt`。状态：关闭（2026-11-14）。原始红测日志保留，真实模型与浏览器限制不变。

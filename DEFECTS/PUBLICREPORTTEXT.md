# PUBLICREPORTTEXT 独立验收缺陷

隔离候选 `/workspace/mcis-report-text-handoff-20261114`。独审只新增测试/报告，不修改实现。

## D01 — 已公开声明未对全部导出字段失效（需修复）

原冻结 `logs/PUBLICREPORTTEXT-impl-hashes-frozen.txt`。`web/src/reportTextHandoff/Panel.tsx:7` 的 key 覆盖案件/证据编号、双摘要、metadata，但未覆盖导出的 fileName、byteLength、registeredUtc。对每个字段单独换入结构合法回执，表单仍保留原地址/勾选及可用导出按钮。原声明针对旧字段，新字段没有重新声明；与组件注释、文档“回执版本/元信息改变重置交接”不一致。

复现：独审 `receipt fileName/byteLength/registeredUtc change clears public declaration` 3 项失败。换入回执保持摘要字段不变，用于检验本地声明边界；此测试不声称当前诚实服务会在同一摘要下修改原登记字段，也不声称存在摘要碰撞。该组件不重算请求摘要，不能单靠摘要字符串替代所有已声明字段的状态失效。

裁定：key 绑定全部导出的回执字段，任何变化清空地址/声明。未要求客户端补造完整真实性认证。

## D02 — 创建下载元素异常泄漏 Blob URL（需修复）

`web/src/reportTextHandoff/model.ts:33-35` 在 try/finally 之前先分配对象 URL 再创建元素。注入 document.createElement 失败，下载未开始，但对象 URL 不撤销。独审 `element construction failure leaves no unrevoked object URL` 失败：分配1、撤销0。该边界先由实现者提示，独审独立注入复现。

裁定：元素创建应先于 URL 分配，或纳入覆盖所有分配后异常的清理块；保留显式失败及原输入，不自动重试。

## C01 — 人员字段措辞（澄清）

UI“不含…人员”容易被读作导出中绝无人名；标题和来源仍保留原文，可能含人名。文档已有正确限定。建议 UI 同样写明不导出提取人/登记人字段，标题/来源中人员信息须人工核查。没有要求自动删改原文。

## 初次独审记录

20 个具名用例：16 passed / 4 failed。完整输出 `tests_acceptance/PUBLICREPORTTEXT/initial-results.txt`。6项原冻结哈希匹配。未调用模型、启动服务、浏览器绕沙箱、提交或推送。

## r1 复验裁定（2026-11-14）

新冻结 `logs/PUBLICREPORTTEXT-r1-impl-hashes-frozen.txt` 6/6匹配。原20具名用例未删除或改写，复跑20 passed / 0 failed；完整输出 `tests_acceptance/PUBLICREPORTTEXT/r1-results.txt`。

- D01：已修复并关闭。新增fileName/byteLength/registeredUtc到状态key，三条失败断言现通过。
- D02：已修复并关闭。创建元素在分配URL之前，故障不再残留URL，失败断言现通过。
- C01：已澄清。UI明示不导出提取人/登记人字段，自由文本仍可能有人员信息须核查。

无未关闭的本切片阻断。受限独立验收通过；未验收真实浏览器磁盘下载、身份认证、来源真实性或任何OCR/模型能力，不建议据此宣称可部署。初始冻结与失败记录保留。

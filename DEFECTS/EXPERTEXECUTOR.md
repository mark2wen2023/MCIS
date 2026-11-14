# EXPERTEXECUTOR 独立缺陷裁定

## D01 — Bridge审计缺口未传播到复合回执完整性（需修复）

原冻结 `logs/EXPERTEXECUTOR-impl-hashes-frozen.txt` 10/10匹配。首批独审17例16通过1失败，见 `tests_acceptance/EXPERTEXECUTOR/initial-results.txt`。

独立测试在真实Pi/脚本提供方循环中令Bridge._record在scripted_model_requested抛出合成OSError。执行器正确拒绝意见并清理进程；Bridge.auditComplete为false。然而Executor.receipt顶层receiptComplete和本次run.receiptComplete仍为true，仅嵌套Bridge记录显示缺口。与README“任何审计写入故障粘性标记receiptComplete=false”不一致，复合回执消费者可能误认审计完整。

裁定：顶层完整性必须覆盖Bridge审计层；本席可关联审计缺口也须显式不完整。issue阶段尚无run时，顶层仍须false。缺口不可因后续记录成功或重复读取回执恢复为true。不要求修改旧冻结Bridge行为或回滚已正确接纳的历史意见。

本缺陷不代表发生真实提供方请求或事实写入；测试始终仅脚本提供方。

## r1裁定（2026-11-14）

D01已修复关闭。Executor.receipt聚合一次Bridge audit，auditComplete非true时顶层receiptComplete粘性false，所有依赖共享审计轨迹的run也显式不完整；issue阶段无run仍顶层false。六阶段故障注入（issued/request/response/tool/done/exit）及修复记录函数后重复读取均通过。

最终25独立用例通过；开发及旧相关84+独审25合跑109通过；10项新冻结前后匹配。初始失败日志与断言保留。无当前有限协议切片阻断；真实DeepSeek/模型质量、生产身份/案件、持久化及真实提供方预算仍不在本次验收能力内。

# EXPERTEXECUTOR 独立验收

目录 `/workspace/mcis-expert-pi-executor-20261114`，基线0a4bf2224fc29afe08df9231aa0aad23dffca72f。仅审新执行器与Bridge公开poll；独审只新增本目录及DEFECTS，不改实现、既有冻结或分支。

## 初次结论

原10项冻结匹配。17独立用例16通过1失败（initial-results.txt）：D01 Bridge审计故障未传播至执行器顶层完整性。意见未接纳、进程已清理，但复合receiptComplete仍true，须修复后再裁定。后续独审扩展为25具名/参数化用例。

## 验证方法与范围

真实进程案例使用固定已有Pi1.5.2运行器，提供方始终是脚本_fixture。完整两轮4个进程实际得到12次脚本model协议请求/8次工具调用；上一完整轮意见数量0/0/2/2；没有真实DeepSeek请求。检查执行层真实进程观察与Meeting/Bridge模拟层字段分离、runtime/bridge两条hash链、Meeting快照重放、回执深拷贝。

故障矩阵：Bridge issued/model请求/响应/tool/done/exit六审计阶段、Executor五审计阶段；done后额外数据、正常done但领进程不退出、WNOWAIT保留领进程PID至自有组清理、正常领进程退出后子孙清理、静默/EOF挂起/管道背压三种截止与fd回收；合成环境秘密不继承。第五model请求在调用_fixture之前被预算拒绝，预取消不启动进程。故障包装进程/假子进程明确只用于监管边界，不算真实Pi能力成功。

进程等待均有测试超时和finally取消；截止测试注入时钟120秒，不声称实际等待120秒。进程组测试只观察本次创建组；不推导能杀死主动脱离进程组的任意不可信代码，也不宣称回收所有后代内核状态。此执行器不是OS沙箱。

所有提供方均脚本；测试不读取真实凭据，环境净化仅放入SYNTHETIC字符串。无服务监听、网络请求、模型调用、部署或推送。复跑使用：

```
PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q tests_acceptance/EXPERTEXECUTOR/test_independent.py
```

## 能力限制

真实Pi进程与其退出只是本机观察；脚本标签不构成模型推理/主持质量验收。上下文完整写入管道不证明阅读或理解。回执未持久化、未签名、不认证作者/模型身份；不提供外部真实请求/计费证据。现有budget只计脚本协议请求。没有安全凭据入口、真实DeepSeek适配、生产身份/案件权限或可部署声明。依赖仅版本/固定脚本摘要检查，不宣称完整供应链认证。

## r1最终裁定（2026-11-14）

实现者按D01修复复合回执完整性：空闲receipt聚合Bridge auditComplete，发现缺口即粘性置顶层false及共享轨迹相关runs false，issue失败无run时仍顶层false。不追溯删除已接纳意见，不把失败后记录成功当补全缺失审计。

原失败断言扩展的六阶段故障及粘性检查均通过。最终 **25独立用例全部通过（2.58s）**，见r1-results.txt；与执行器19+Bridge/Meeting65合跑 **109 passed in 4.63s**，见r1-combined-results.txt。新冻结logs/EXPERTEXECUTOR-r1-impl-hashes-frozen.txt **10/10前后匹配**，见r1-hashes.txt。初始16通过1失败证据保留。

D01关闭，当前受控Pi/脚本协议切片受限独立验收通过，无未关闭阻断。报告中的真实能力差距和所有限制不变；109通过不能解释为真实DeepSeek会议、语义能力、持久审计或身份认证验收。独审文件已落盘，不修改实现、提交或推送。

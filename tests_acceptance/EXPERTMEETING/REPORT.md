# EXPERTMEETING 独立验收报告

日期2026-11-14；隔离目录 `/workspace/mcis-expert-meeting-20261114`，基线a686c851333428d35374fb1596b6772a1cc6e9a8。范围仅新增research/expert_meeting纯内存模拟状态机；无模型/网络/服务/部署/推送。独审仅新增本目录测试/报告及DEFECTS，不改实现。

## 裁定

r1受限独立验收通过，无未关闭的当前切片阻断。初次28独立用例27通过1失败；D01证明精确已接受submit重放绕过合作式600秒截止，保留initial-results.txt和原断言。实现者调整非终态截止检查顺序后，**36独立用例全部通过**；与34开发测试合跑 **70 passed in 0.61s**。分别见r1-independent-results.txt及r1-combined-results.txt。新冻结logs/EXPERTMEETING-r1-impl-hashes-frozen.txt **6/6前后匹配**，见r1-hashes.txt；原冻结初验6/6匹配。

## 实际验证

- 第一轮后发席次看不到同轮新意见；第二轮两席收到同一完整上一轮快照，包括自己和同伴意见；第二轮先发新内容不污染同轮后发contextDigest。分歧与标签相同保持未决/非共识，不升级事实。
- ticket/context错误、重复item/遗漏item、非法引用/未知字段/空不确定性/超过2000字符均拒绝，状态及审计导出不变。
- 36次并发精确提交仅接受一次；两个不同内容的并发同ticket提交只有一个成功。12次停止/提交竞态均产生可顺序解释的终态和可重放审计。测试不宣称穷尽调度或跨进程并发。
- 599.999秒/600秒截止边界；snapshot只读不触发截止；NaN/±Inf/bool/string时钟输入拒绝且状态审计不变；旧精确提交在截止后触发timed_out；已经停止的精确重放保持幂等不复活。
- unknown保留中断ticket及已分配额度，拒绝后续提交/重发；半轮人工停止保留单方意见，不虚构比较或共识。
- 审计hash构造故障注入在提交前抛错，状态/审计无部分写入，恢复函数后正常可继续；快照和调用方输入深拷贝不能追改历史。
- 重新计算事件hash仍不能把非法转换、倒退时间、事实激活/模式/认证篡改或无效noop事件伪造成可接受重放；重复JSON键、非有限数、病态嵌套、超1MiB输入拒绝。
- 两轮全部rationale/uncertainty达2000汉字边界可正常导出并verify，正常完整链实际10个变更事件。32是实现事件数上限，不是本次真实产生32事件或模型调用数。
- 对最大输入完整流程禁止socket构造及原engine的run_group/_remote，仍通过。只读取已冻结公开packet；没有凭据或真实网络执行。

复跑命令：

```
PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q tests_acceptance/EXPERTMEETING/test_independent.py
PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q research/expert_meeting/test_machine.py tests_acceptance/EXPERTMEETING/test_independent.py
sha256sum -c logs/EXPERTMEETING-r1-impl-hashes-frozen.txt
```

## 剩余能力差距

“海青君”是确定性软件排程标签，不是真人、认证主持或已运行模型。所有意见为合成输入；contextDigest是数据绑定，不证明阅读、理解或推理。没有Pi会议适配器、DeepSeek请求、真实费用预算执行、真实在途请求取消或正式工作台UI。每席4/8及总16/32是预留配额，不是实际调用计量。合作式deadline仅在act/tick时观察，无后台时钟或外部任务强杀。

状态与审计同处内存，无持久化崩溃恢复保证。导出重放只验证自洽，不能认证作者、会议实际发生、来源真实性或事实；可自行构造另一条自洽模拟链。未验证恢复运行，因为没有恢复入口。单进程锁测试不证明多进程部署安全。

真实能力下一步需要新的明确授权/披露及安全凭据渠道、公开冻结材料上的真实两轮DeepSeek/Pi调用证据、实际同伴上下文/预算/取消/未知结果验收，以及独立身份和案件权限边界。不能用本次70通过替代这些验收。

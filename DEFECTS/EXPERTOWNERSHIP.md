# EXPERTOWNERSHIP 独立裁定

2026-11-14：所有权修复受限复验通过，14独立用例通过，5项冻结匹配。

确认SIGCHLD忽略/自定义handler启动前拒绝；ECHILD、已回收returncode、信号改变或PID不匹配后粘性拒绝，cleanup不向已丢失所有权的PID发送killpg。实际外部reaper的Pi、provider及复合执行路径回执保留unknown/未回收/不完整；正常mock执行和截止回收通过。

未发现当前明确支持宿主条件内的新阻断。独占reaper和稳定默认SIGCHLD仍是强制前置条件；check→kill之间不是原子PID能力，对违反前置条件的任意并发宿主不得宣称无风险。真实运行HOLD不因本报告解除。

报告与复现见tests_acceptance/EXPERTOWNERSHIP/REPORT.md。未找到原指定review-pi8/test_reviewer_ownership.py，未宣称已跑。独审未改实现、联网、调用真实模型或推送。

## D01 — waitid符号存在但系统调用不可用（新增待修，取代上文最终通过裁定）

父协调者提出能力探测问题后，独审确认：启动前仅callable/常量检查，NotImplementedError或ENOSYS会在真实spawn之后才发现。此时已经失去可依赖的回收手段，可能遗留执行中的worker。独立测试用Popen计数后立即抛错，不实际启动进程；两个变体均证明启动尝试发生，红测见capability-initial-results.txt。

建议require_support在启动前以自身PID进行不消费子进程的waitid探测，预期ECHILD；NotImplementedError/ENOSYS或不符合预期结果均拒绝。新增边界修复与复验前本次所有权验收待定，真实HOLD不变。

## r1最终裁定

D01修复关闭：自PID probe只接受预期ECHILD，实际系统调用不支持或返回异常时均在spawn前拒绝。保留两条原红测，新增probe异常返回及不消费既存子进程测试。最终18独立用例通过，新5项冻结前后匹配。

r1在明确宿主支持条件下受限通过；不表示获得原子PID能力，不支持外部reaper并发夺取所有权，不解除真实运行HOLD。独审证据与限制详见REPORT末尾。

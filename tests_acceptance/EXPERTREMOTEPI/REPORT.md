# EXPERTREMOTEPI 独立安全验收

2026-11-14；隔离目录 `/workspace/mcis-expert-remote-pi-20261114`，基线1b897f7。只新增独立测试及报告，不改实现或冻结。

结论：当前远程路径的离线协议边界受限独审通过。**17独立用例通过（3.87s），15/15冻结匹配**。结果与哈希分别见results.txt、hashes.txt。没有重跑父协调者已完成的195项全量回归，不混计为独审覆盖。

## 实际验证

- 固定实际Pi配合显式remote_mock Python worker完成两轮四席；4个Pi回合、12个worker attempt、12次Bridge模型协议预留、8tool。没有对同一reserved请求二次扣数。上下文前轮意见数0/0/2/2；所有worker/顶层/run保持mock及realDeepSeekExecuted=false，响应模型元数据为MOCK-NOT-DEEPSEEK。
- 父进程禁止socket.connect、旧engine._remote/run_group与Executor脚本_fixture；真实worker仅以--mock运行HTTP替身。不在父进程假装有真实提供方结果。
- Meeting事件为4次submit_provider_response，无submit_simulated；scripted/remote构造错配及向remote Bridge调用scripted_response拒绝，不写意见。
- 七种受控假worker输出：result=null、缺assistant、坏metadata、identityVerified=true、mock模式错配、尾随数据、坏UTF8均拒绝，错误保留processStarted=true/leaderReaped=true/exitObserved=0，dispatched保守true，fd无泄漏。此为协议故障测试，不计作实际Pi成功。
- 四类不合作worker：静默、提前关闭stdout、输出正确JSON但不退出、stdin背压；父绝对截止0.15s触发并在2s测试窗口内回收，保留unknown与fd基线。未声称等待完整120秒或内核硬实时。
- 正常领进程输出后留下同组睡眠后代，返回成功前自有组清理使后代消失或成为待系统回收僵尸；不宣称本进程回收了全部后代。
- 人工取消与既有Bridge120秒截止均打断睡眠worker、清理worker和Pi、保留unknown；复合回执校验接受合法部分结果。旧截止使用可控时钟，不因新Adapter重置。
- 第一角色已完成后第二角色在途取消，保留原已接受意见，两个run状态为completed_unverified/unknown、provider最后attempt unknown、会议stopped_by_operator；复合校验通过，不把部分结果补成全场完成。
- 完成mock回执改顶层realDeepSeekExecuted或transportMocked被复合验证器拒绝。

## 预审问题

冻结前只读发现isolated.request未先验证result类型，在try/finally外写result['worker']可能抛TypeError并丢进程观察。实现者已在正式冻结前修复。独审正式七种畸形worker测试证明拒绝时保留清理元数据；没有冒称保留了修复前动态红测。

## 复跑

```
PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q tests_acceptance/EXPERTREMOTEPI/test_independent.py
sha256sum -c logs/EXPERTREMOTEPI-impl-hashes-frozen.txt
```

## 剩余限制

没有真实DeepSeek调用、真实凭据或在线模型身份/质量/usage验收。mock HTTP和固定Pi进程通过不等于专家能力；remote模式仍须安全凭据、批准和公开材料真实验收。回执与哈希只证明本地自洽，不认证模型/作者或事实；真实路径布尔值也是本机观察声明。

worker监管不是OS沙箱；只验证自有进程组，主动逃离进程组或内核停滞不在保证范围。内存attempt账本不支持崩溃恢复、持久化发送前预留或自动重试；请求预算不是金额上限。当前没有多轮工作台、生产身份或案件授权验收。测试未调用网络/模型、未启动服务、未提交推送。

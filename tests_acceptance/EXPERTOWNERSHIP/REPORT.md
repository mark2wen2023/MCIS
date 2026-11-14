# EXPERTOWNERSHIP 独立安全复验

目录 `/workspace/mcis-expert-remote-pi-20261114`，分支codex/expert-pi-ownership-fix-20261114，基线8f2fa05。独审仅新增本目录和DEFECTS，不改实现或冻结。

结论：**14独立用例通过（1.15s），5/5冻结匹配**。见results.txt、hashes.txt。本次已观察的所有权丢失故障路径均未向失去所有权的PID/PGID发送killpg，Pi/worker如实标未知/未回收/不完整。无本切片新增返工阻断。真实调用仍保持HOLD；独审不授权解除HOLD。

## 实际证据

- SIGCHLD=SIG_IGN和自定义handler在Pi、provider启动前拒绝，Popen替身断言未启动；另在独立宿主子进程设置真实SIG_IGN复现启动前拒绝。
- ECHILD、Popen.returncode已赋值、信号配置改变、waitid返回不同PID均触发粘性丢失；即使随后信号/waitid条件恢复，重复cleanup仍不发送killpg。
- observe第一次成功后，cleanup再次waitid遇到ECHILD，未信号，证明cleanup不复用旧观察。
- 实际外部reaper先waitpid回收一次短命Pi替身或provider替身，随后控制器检测丢失；两条路径均无killpg。Pi回执unknown、leaderReaped=false、groupKillSent=false、receiptComplete=false；provider错误记录processStarted=true、leaderReaped=false，保守dispatched=true。
- 在真实Pi远程mock执行链中只对provider执行外部回收：不得kill provider旧PID；仍正常清理独自拥有的Pi组。复合回执provider attempt unknown、worker未回收、整体不完整；Pi领进程回收记录正常，没有伪装整体成功。
- 正常cleanup对实际睡眠子进程使用自有waitid回收；Popen.wait被设为失败仍通过，避免其ECHILD掩盖行为。
- 正常实际Pi+3个MockHTTP worker单席完成、回执完整且realDeepSeekExecuted=false；worker0.12秒截止回收与fd基线回归通过。

## 复跑

```
PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q tests_acceptance/EXPERTOWNERSHIP/test_independent.py
sha256sum -c logs/EXPERTOWNERSHIP-impl-hashes-frozen.txt
```

未重复父协调者已完成的222项大集合，未混入本独审计数。指定review-pi8/test_reviewer_ownership.py在此环境未找到，本报告没有声称运行它。

## 重要剩余约束

这些检查不是原子PID能力。observe与killpg之间仍要求宿主遵守独占reaper、SIGCHLD稳定为默认、不得另线程poll/wait/reap。若外部reaper恰在检查后抢先回收，当前接口不能提供竞态不可能发生的证明；实现docstring与合同明确此类宿主不支持。不得将本次故障复验说成任意宿主下绝对消除PID复用风险。

检测丢所有权后不发killpg，可能留下无法由本控制器安全处置的组成员；未知/未回收/不完整是正确保守记录，不应补造已清理。异常内核状态、主动逃组后代及其他宿主信号系统未穷尽。没有真实模型/网络/凭据、服务、公开监听、推送或部署。仅一席正常mock回归，不替代完整模型会议能力验收。

## 新增能力边界待修（取代前述最终通过裁定）

父协调者随后提出waitid是否需真实系统调用探测。独审追加NotImplementedError/ENOSYS两项不创建子进程的故障测试，证明旧require_support放行了Popen尝试，见capability-initial-results.txt。14项既有测试仍是已完成事实，但新增D01解决前不能给最终通过。待r1加入启动前自PID安全probe并复验；真实HOLD保持。

## r1最终裁定（取代待修状态）

D01已修复：启动前自PID执行精确waitid选项组合，仅ChildProcessError视为支持；NotImplementedError、ENOSYS或异常返回一律拒绝。observe不重复自PID probe，但保持原有信号/所有权检查与独占reaper约束。

原14例及2红测全部保留，再增加异常返回拒绝和自PID probe不消费现存子进程两条，最终 **18 passed in 0.98s**，见r1-results.txt。新冻结logs/EXPERTOWNERSHIP-r1-impl-hashes-frozen.txt **5/5前后匹配**，见r1-hashes.txt。初始结果、两条红测与原冻结保留；未重复大集合。

r1受限独审通过，D01关闭，无当前支持条件内的新增返工阻断。此前明确的非原子PID能力、独占reaper/稳定SIGCHLD宿主前置条件及真实运行HOLD完全不变。本报告不授权真实调用，也未声称已运行缺失的review-pi8原指定脚本。

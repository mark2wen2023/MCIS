# 真 Pi 运行器与脚本提供方：受控协议执行器

基线 `0a4bf2224fc29afe08df9231aa0aad23dffca72f`。此前Bridge已推独立分支，本片另立分支，只新增本目录及Bridge公开poll接口；不改状态机、Pi运行器、其他候选/案件服务。无安全凭据，因此本次只验证**实际Pi进程与脚本提供方的协议**，没有真实DeepSeek会议或模型质量验收。

## 调用范围

`Executor(bridge).run_turn(role)`同步监管一个角色进程。程序固定为既有 `research/expert_group/pi-runner.mjs`，启动前核对其SHA-256 `c826f7ac90fdb997c416505b67e9ee143cdcc56b9f32b0898eca2d7e5b7a5511`，Pi core/ai声明版本须1.5.2。使用仓库锁文件准备依赖；版本及脚本摘要检查不是完整供应链认证。没有可由用户输入的脚本、URL、模型提供方或凭据参数。

真实运行器导入Agent并通过stdio发model/tool/done。Python端只调用固定 `_fixture` 产生明确脚本占位响应，再由Bridge校验/回填；不会调用 `_remote`、环境密钥或远端服务。真实进程运行不等于真实模型推理。下一轮仍须控制器显式调用Meeting.start_round；演示CLI的显式参数一次授权固定两轮脚本流程。

## 监管与完成门禁

- Linux/POSIX，使用绝对Node程序路径、净化环境（仅PATH/LANG）、独立会话/进程组，不继承HOME、NODE_OPTIONS、密钥或代理设置。此配置不是OS网络/文件访问沙箱：仅运行固定可信代码，没有网络提供方；不得用来执行任意不可信脚本。
- stdin/stdout非阻塞，管道单条262144字节，总stdout2MiB、最多32消息。写入背压和无输出等待都每50ms附近合作检查Bridge.poll；轮120秒和会议600秒沿用既有门禁，不对任意内核停滞声称硬实时保证。EOF而进程未退出不会当完成，也不忙轮询。
- `cancel()`可由另一控制线程调用：设停止标记、终止会议；执行线程随后清理自己的进程组。未知协议结果不自动重试。一个Executor同时只能运行一席；Bridge维持全会议预算，不随新子进程重置。
- done标记仍须经过Bridge候选/引用校验；正常退出、stdout完全消费及无尾随数据、进程组清理和领进程回收都发生在Bridge.exited提交前。非零退出、额外输出、取消、超限或回执记录失败不提交完成意见。
- 用waitid(WNOWAIT)观察退出，不提前回收领进程，以保留本实例PID/PGID所有权；向自建组发送SIGKILL后wait回收领进程，再关闭管道/selector。要求本控制器独占所启动子进程的wait管理；不支持嵌入另有自动子进程回收器的宿主。`groupKillSent`表示清理信号步骤，`leaderReaped`表示领进程已回收，不宣称认证或回收所有内核状态下的后代。

## 共享预算与来源回执

空闲时 `receipt()` 返回内存快照；run_turn期间拒绝生成混合时点快照。包含：

- 本Executor观察的进程启动/退出、脚本SHA、清理、最终接纳状态；runtimeEvents记录哈希链元数据。
- `context_written_to_pipe`只表示完整写入管道，并不证明模型/人阅读理解。第二轮双方仍只有上一完整轮，不读同轮同伴。
- 原Bridge全会议modelAttempts/toolCalls与哈希链，限额仍4/8每席、总16/32；这里modelAttempts是**脚本协议请求数，不是实际提供方请求或计费**。
- 原Meeting审计快照，可用其verify_snapshot重放。Meeting/Bridge中的piExecuted/realPi=false描述未观察外部进程的模拟状态层；真实进程观察单独记录在本层runs，不篡改既有冻结记录，也不把这些字段混成能力认证。
- 顶层realDeepSeekExecuted=false/authenticityVerified=false；所有模型意见仍scripted/unverified，factActivated=false。任何审计写入故障会粘性标记receiptComplete=false。

回执不持久化、不签名、不恢复任务，也不是完整外部提供方回执。父状态已经接受的意见不会因后来操作者停止而被追溯删除；新增失败席次不能伪造完成。运行器和进程退出属于本机观察，不是作者/模型身份认证。没有案件写入、文件上传或部署。

## 使用和验证

从仓库根准备既有依赖（不要传聊天密钥）：

```
npm ci --prefix research/expert_group --ignore-scripts
PYTHONPATH=. service/.venv/bin/pytest -q research/expert_executor research/expert_bridge research/expert_meeting
service/.venv/bin/python -m research.expert_executor.demo --scripted-pi > /tmp/pi-protocol-receipt.json
```

本环境复用已有Pi1.5.2依赖目录，Node v24，service虚拟环境；测试冻结不包含node_modules。新增18项执行器测试+原65项，共83通过：实际固定Pi两轮四进程、12模拟模型协议请求/8工具、上一轮意见数0/0/2/2；另用明确假子进程测试坏输出、非零退出、异常尾随、环境隔离、背压/无输出/EOF挂起取消与截止、进程组及fd清理、回执故障。截止使用可控时钟，不宣称等待了完整120秒。伪子进程案例不作为真实Pi成功证据。

未来真实DeepSeek适配仍缺：安全凭据注入、新共享意见披露授权、实际请求前持久预算、真实请求/响应和未知结果回执、模型质量验收、生产身份与案件边界。本片没有提供真实传输入口，不能靠换一个模式标志声称这些能力已完成。

## r1 复合回执完整性

独审复现Bridge审计失败时其auditComplete=false，但执行器外层曾仍标完整。现在任何Bridge不完整状态都会传播至顶层及依赖该共享轨迹的所有run，粘性保持false（包括issue阶段尚无进程记录的失败）。不改变已观察进程退出、不补造预算事件，也不抹去已有模拟意见；只拒绝把不完整共享轨迹说成完整回执。原红测保留。

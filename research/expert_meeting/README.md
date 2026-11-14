# 海青君主持：有界会议编排状态机（仅模拟）

## 已有能力与缺口

本片基线 `a686c851333428d35374fb1596b6772a1cc6e9a8`。其 `research/expert_group/engine.py` 的 COMMON 明确禁止 sibling review，run_group 依次执行两个独立Pi角色后结束；没有主持议程、跨轮意见上下文或显式继续会议接口。原执行器已有单次取消/截止/未知结果边界，不应重复冒充新增能力。

另只读核查 PR56 基线254167e：`contracts/W20.3-agent-overview.md` 明确六角色配置登记，不存在主智能体会话/调度/实时心跳；`service/mcis_service/agents/router.py` 只有people_ops本地笔录提取路径，其余未连。未从97项预览栈提取代码。本片不替换现有候选，不接正式案件或工作台UI，不改时间对照/查重/专家执行器。

用户期望的海青君主持、专家逐轮读同伴意见和人工可终止，仍与真实Pi会议有距离。本片完成的是下列可审计状态约束，**不是**真实主持推理或新DeepSeek会议验收。

## 状态合同

`Meeting` 是单进程锁保护的纯内存控制器；“海青君（软件主持）”是确定性排程标签，不是真人/认证身份。仅加载固定公开YANGZE22片段，保留a686的精确引用校验。所有提交必须显式使用 `submit_simulated`，输出永远 simulation_only/modelExecuted=false/piExecuted=false/factActivated=false/consensusComputed=false。

- `ready → start_round → round_open`，顺序发放来源归属、限定词边界两席次。
- `issue_turn` 发放会议/轮次/角色绑定ticket与contextDigest。第一轮无同伴上下文；第二轮两个角色均读取上一**完整轮**的同一快照，包括各自和同伴意见。同轮意见不泄露给后发角色，避免顺序偏差；改变首轮意见会改变第二轮contextDigest。
- `submit_simulated` 需回传ticket/contextDigest、每主张一份原文引用/解释/不确定性。回传摘要只是数据绑定，明确不证明模型或人实际阅读/理解。字段最多2000字符（比原执行器12k更小）。不把旧/异会话ticket套到新席次。
- 一轮收齐后保留两个标签：`different_labels_unresolved` 或 `same_labels_not_consensus`，不投票、不自动合并意见、不升级事实。第一轮进入 `round_review`，必须显式 `start_round` 才继续；第二轮结束为 `completed_unverified`。
- 人工调用 `stop` 在所有未终止状态生效，保留已收意见/当前被中断ticket。后续发放/迟到结果拒绝；重复stop无副作用。相同issue/完全相同已收submit是本地幂等无事件，变更重复提交拒绝。旧已接受submit重放不会恢复被终止会议。
- `fail_turn` 的 failed/unknown 均终止，不自动重试。unknown保留不确定结局，不假定未发/已撤销请求。本片没有真实在途请求，因此stop只保证状态机停止后续安排，不声称取消真实HTTP/Pi子进程。

最多2轮、4席次；每席次预留4模型轮/8工具，总预留16/32。这只是未来执行器的配额，**不是实际请求计量、费用上限或已接通的模型预算执行器**。未知/失败席次不回收重试配额。600秒是单调时钟合作式截止：下一次act/tick发现到期即终止；无后台定时器，不会强杀外部任务。时钟倒退/非有限值拒绝。只读snapshot不触发截止。

每次有效变化同时在内存提交状态与哈希链事件，事件记录操作、相对经过毫秒、前摘要和新状态摘要。最多32事件、单操作64KiB、导出1MiB。快照是深拷贝；入参变化不能追改历史。`verify_snapshot` 重放所有转换、校验链和最终状态；只证明本地自洽，任何人仍可构造另一份自洽模拟，无签名、身份认证或真实执行证明。显式export只返回字节，不上传、不写文件、不自动存储；崩溃前未导出的内存会丢失。验证不是恢复运行/自动续跑入口。

## 使用与复跑

从仓库根，使用已有service虚拟环境：

```
PYTHONPATH=. service/.venv/bin/pytest -q research/expert_meeting
service/.venv/bin/python -m research.expert_meeting.demo --simulate > /tmp/meeting-simulation.json
service/.venv/bin/python -m research.expert_meeting.demo --verify-stdin < /tmp/meeting-simulation.json
service/.venv/bin/python -m research.expert_meeting.demo --simulate --stop-after-turn 1
```

`--simulate` 输出明确标为脚本占位的两轮分歧，绝不调用模型。`--stop-after-turn` 是脚本停止演示；真实操作者可在自己的控制循环调用 `meeting.act({'type':'stop'})`，没有浏览器停止按钮。示例Ctrl-C仅尝试停内存状态，不宣称解决真实任务取消。本片没有默认执行模式、模型参数、密钥读取或远端API。

## 下一纵切及验收门槛

1. 设计真实Pi会议适配器及新的披露摘要，覆盖角色之间共享模型意见、主持提示、轮数/请求/工具/总时限；不能沿用a686禁止同伴读取的独立模式提示和授权摘要。
2. 安全凭据注入与明确授权后，仅使用公开冻结报告，真实DeepSeek完成至少两轮；保留实际请求/响应/模型工具回执，验证每轮实际收到正确前轮快照，区分字段声明与调用证据。
3. 实际执行器每请求前消耗预算，合作式/硬截止取消子进程，未知HTTP结局不得自动重试；状态持久化故障及人工终止竞态必须另验。本片没有这些真实执行保证。
4. 引入会话UI之前解决生产身份与案件访问边界；本片没有接入正式案件。真实模型语义质量由公开材料、来源限定词、分歧保持和人工复核检验，不以脚本标签吻合算通过。

## r1 截止优先级

独审复现旧已接受submit在到期后重复，曾先返回幂等结果而未终止另一个活动席次。现在非终止会议先检查截止，再处理精确重复；已终止会议的重放仍不复活。相关初始红测保留，未放宽人工停止或未知结局边界。模块只读固定公开packet，并非完全无文件读取。

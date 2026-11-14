# EXPERTMEETING 独立裁定

## D01 — 精确已接受提交重放绕过合作式截止（阻断待修）

初始冻结 `logs/EXPERTMEETING-impl-hashes-frozen.txt` 6/6匹配。
`research/expert_meeting/machine.py` 的 `_transition` 先对精确已接受submit直接return，后检查elapsed。复现：第一席已接受，第二席active，时钟达到600秒，提交第一席的精确原action，返回round_open而非timed_out。因此一次合法act观察到截止仍不终止，与README“下一次act/tick发现到期即终止”不符。

独立断言 `test_accepted_replay_at_deadline_terminates_active_meeting` 初次失败；首批28用例27通过1失败，保留 `tests_acceptance/EXPERTMEETING/initial-results.txt`。应只对尚未终止会议优先执行截止转换，再处理幂等；终态的已接受精确重放仍不得改变终态或复活。不要求后台计时器或真实模型取消。

## C01 — 模块 No IO 描述（非阻断澄清）

constructor/verifier读取固定公开packet；模块docstring不宜称完全No IO。应明确无executor/network/writes、只读取冻结公开材料。此点先由实现者自查提出，独审核对调用load_packet确认。

## r1修复裁定（2026-11-14）

D01已修复关闭：对非terminal状态，deadline优先于精确重复提交分支。原红断言保持，现通过；额外验证已停止会议的精确旧提交在700秒仍为原终态且导出不变，未复活。

C01已澄清：模块docstring明确无executor/network/credentials/writes，读取冻结公开packet。

独审36/36通过；与开发34合跑70/70通过；新6项冻结前后匹配。初始27pass1fail证据保留。当前有限模拟状态机无未关闭阻断；真实模型/Pi会议/网络取消/认证/持久化能力仍未实现或验收，不能以本裁定宣称满足真实专家会议全流程。

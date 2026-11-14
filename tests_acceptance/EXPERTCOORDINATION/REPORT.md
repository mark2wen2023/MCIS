# EXPERTCOORDINATION 独立验收

r1最终10项独立测试通过（0.07秒），冻结3/3一致。初始3项失败保留initial-results.txt；最终r1-results.txt、r1-hashes.txt。复跑：`PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/python -m pytest --import-mode=importlib -q tests_acceptance/EXPERTCOORDINATION/test_independent.py`。

D01：原_refresh后的第二次Meeting.act时钟采样若NaN，异常绕过封闭，pending可留待后续升级。stop/settle_failed/settle_unknown三项红测独立复现。r1统一_apply捕获时钟/协议异常，blockedReason永久保留，pending转unknown，后续returned拒绝；三项原断言未改，均通过。

其他独立覆盖：两轮四席合计16model/32tool=48条递增预留，重复settle不退款或加额；8线程同时reserve仅一胜；receipt/reserve/settle/action四公共边界观察到期后pending未知，不可升级为returned；人工停止后重复unknown幂等、变更结算拒绝。receipt明确不认证身份/执行、不授权网络、不声称硬取消。

裁定：本次r1新增协作门禁及D01修复范围通过。**父协调者另报告继承Meeting浮点截止缺陷：start+600经差值毫秒int可能成为599999，将另候选修复。该已知依赖缺陷未在本候选改动，也未被本次从0起点的到期测试排除；不得称精确截止已验收或依赖已全部通过。** 在修复/复验前继续HOLD；本报告不放行真实runner或严格截止使用。

本gate是合作式采样，无公共调用时不会运行；没有watchdog、原子网络许可、取消确认或持久预算恢复。意见可无attempt记录被纯协议接受，不能当真实执行证据。未运行模型、网络或修改冻结实现；未合计父测试数。可保存本地r1候选，后续晋级需处理上述依赖缺陷。

# EXPERTCOORDINATION 独立缺陷

## D01 阻断：二次时钟失败未永久封闭

action与settle先_refresh成功后，stop或failed/unknown再调用Meeting.act并再次采样时钟。第二次NaN异常绕过_refresh的封闭处理；后续恢复正常时钟时blockedReason仍None，pending尚可被结算为returned_unverified。与COORDINATION.md clock failure permanently seals gate不符。

独立3项红测覆盖stop、settle_failed、settle_unknown，注入[0,NaN]，证据tests_acceptance/EXPERTCOORDINATION/initial-results.txt。未改实现。须统一保护第二次Meeting.act异常；在未知结果后不可继续升级。修复前不通过。

## r1复验

D01已关闭：统一_apply保护所有Meeting.act，三项原红断言不变且转绿。最终10独立测试通过，r1冻结3/3一致，原失败证据保留。

## 已知继承限制（未关闭）

父协调者报告Meeting浮点绝对截止边界：差值乘1000再int可能将start+600变为599999毫秒。将另候选修复；本候选不修改父machine。不能将r1通过解释为严格截止/全依赖安全通过，真实runner与精确截止用途继续HOLD。详见独审REPORT。

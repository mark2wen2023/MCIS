# EXPERTCONNECTED 独立裁定

## D01 — 展示投影预算与阶段矛盾仍被接受（待r2）

父实现者自查提示received最低计数不足。独审用已验证实际MockHTTP回执的投影为基准，独立变更5项：已完成角色模型轮数超过received、not_started角色计数非零、ready带已完成轮、round_review带两轮全部完成、round_open带全部完成席次。parseMeeting全部错误接受，见tests_acceptance/EXPERTCONNECTED/parser-initial-results.txt及parser-boundaries.mjs（0/5通过）。

Python export前的完整回执validator仍会拒绝对应原回执矛盾，因此不声称经受控完整导出链制造了此类错误。问题在build --meeting直接投影或浏览器展示结构检查不够严格，须收紧且保留原红断言。

## C01 — embedded加载状态文字（非阻断）

会议投影已显示但role=status仍称“尚未载入结果”，是旧单轮加载默认文字。建议embedded视图准确说明已载入只读会议投影，仍不认证来源或授权调用。

## 已完成独审

10个Python用例通过，其中一个执行8个独立DOM场景。验证已有实际MockHTTP回执导出、原始文件不变/摘要、禁止覆盖（含输入输出同路径）、symlink/父symlink/FIFO拒绝、并发唯一发布、写入失败无残留、非法回执先拒绝、轮次切换/部分未知/恶意文本/来源分区。未联网、调用模型或重试原生浏览器。D01修复前不作最终通过裁定。

## r3 修复复验（最终）

D01：已关闭。5项原红断言未改，最终r3下全部拒绝；Python完整原件验证边界继续通过。

C01：已关闭。独立DOM确认embedded加载后role=status准确显示已载入只读会议视图。

最终独审12个pytest用例通过（含8DOM及5parser子场景），冻结12/12一致，证据在tests_acceptance/EXPERTCONNECTED/r3-results.txt和r3-hashes.txt。原parser-initial-results.txt保留0/5失败证据。仅离线展示导出范围通过；真实模型与原生浏览器仍未验收，真实运行HOLD保持。

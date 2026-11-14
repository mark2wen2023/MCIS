# 机器转写草稿 v2 独立复核

限定合同范围通过，未发现阻断缺陷。作者21+独立12，共 **33/33通过（0.13秒）**，日志independent-results.txt。

独立覆盖：version/track布尔等类型拒绝、人工审核/说话人身份混淆拒绝、跨evidence拒绝、unknown-current仍先验证输入/输出绑定、unlocated文本同样纳入output摘要、返回深复制且输入不变、父版本声称不自动取得权威。

关键否定测试：完全虚构文本并自洽重算receipt输出摘要、声明claimed_local_execution，仍仅为supplied_snapshot_matches_not_authenticated，executionVerified/sourceBytesChecked/authorizationVerified/admissionAllowed/humanTranscript全部false。receipt不是执行证明，模型/工具/weights哈希均由调用者提供，未查询真实服务或历史链。

v1转换仅为内部重用结构规则，不输出人工记录；机器文档自身保持v2、machine_asr_draft、pending。时间段、未知speaker、大小预算继承已审v1。当前compare仍依赖所供快照，不是权威当前状态/实时撤权检查。

仅离线合成合同测试；未运行ASR、模型或真实录音，不包含API/DB/认证，未修改实现、提交推送或部署。正式使用仍需可信执行回执、实际源字节和授权绑定，不能因通过纯函数测试宣称这些完成。

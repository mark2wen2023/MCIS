# EXPERTBRIDGE 独立验收（2026-11-14）

审查目录 `/workspace/mcis-expert-bridge-20261114`，分支 `codex/expert-pi-protocol-bridge-20261114`，实际 HEAD `649d8656c5f5b3aca93751468c108edd73f5ce61`。实现范围只新增 research/expert_bridge，既有 Meeting、Pi执行器与公开包为只读依赖。

结果：**43 passed，0 failed**，日志 `results.txt`。七项冻结哈希全部一致。独立测试自建协议消息与控制器，不复用开发测试辅助函数。

```sh
PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q tests_acceptance/EXPERTBRIDGE
sha256sum -c logs/EXPERTBRIDGE-impl-hashes-frozen.txt
```

验证包括：

- 两轮四席次通过纯内存协议完成，第一轮无同伴意见，第二轮两角色共享同一上一完整轮快照；候选摘要按ticket/contextDigest/reviews独立重算，4个候选互不混用；父快照与审计哈希链自洽。
- 工具id/name/args/顺序严格匹配，pending工具禁止新模型请求；错误requestId、外来ticket和重复响应拒绝。上下文变化、旧ticket、错误候选不写新意见。
- 重建Bridge不能重置预算；单席4模型/8工具边界及四席总16/32精确耗尽成功，额外单席调用拒绝。返回历史和审计深拷贝不可改内部状态。
- done尚不提交；必须整数0退出且父会议确实接受才显示完成。布尔、浮点、空值、非零退出拒绝。取消后响应/done/exit不能复活，pending请求保守unknown；120秒角色和600秒父会议精确截止均拒绝迟到响应。
- 请求、响应、工具、done和接受尝试阶段审计异常均fail closed，不发表意见且auditComplete=false；父提交未接受也不伪完成。审计不含意见正文。
- 严格单行UTF-8、重复键、无换行、多行、未知操作、超限输入拒绝；伪造引用、重复项目、超过2000字符、未读取先验证拒绝。

所有43项均有autouse禁止桩：socket.socket、socket.create_connection、subprocess.Popen、engine._remote调用会立即失败。未启动真实Pi、网络连接、服务、浏览器，未读取凭据或调用模型。只读取冻结公开包。没有改实现、提交、推送或部署。

未发现当前纯内存协议范围的未关闭阻断。初稿独立工具预算测试尝试在单个响应中授权9工具，继承解析器先行拒绝（更严限制），已将同一边界断言改为8工具后下一响应第9工具，保持原测试意图；这不是实现缺陷。

限制：退出码、响应和计数均为合成控制器声明，不是操作系统/提供方证据。合作式截止只拒绝后续接口操作，未接通进程和HTTP取消。审计仅内存，无持久恢复、真实性认证或真实账单计量。未做真实DeepSeek、真实Pi、浏览器或正式业务权限验收。未来实际Pi适配、秘密隔离、持久请求预算、进程终止及未知提交确认仍需独立实现和验收。

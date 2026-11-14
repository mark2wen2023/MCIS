# EXPERTREMOTE 独立安全验收

目录 `/workspace/mcis-expert-remote-adapter-20261114`，基线93284d8，仅新research/expert_remote。独审未改实现、联网、启动服务、调用模型/Pi或推送。

初始20独立用例19通过1失败：D01空闲cancel后回执halted仍false。原红测保留initial-results.txt；初始5项哈希验过且记录initial-hashes.txt。D02 BaseException由实现者自查提出，独审静态确认；独立执行新增断言时已是修复版，因此不宣称有修复前D02红测。

r1最终 **23独立用例通过**，与 **58开发测试合跑81 passed in 0.70s**，见r1-combined-results.txt。新增SystemExit/KeyboardInterrupt和收到响应后取消与原红测共4条子集通过，见r1-abort-results.txt。

## 独立覆盖

- 真实Adapter.dispatch→真实transport.request→httpx.MockTransport，不替换上层request接口；实际检查官方固定HTTPS URL、POST授权头、固定model/max_tokens/stream、trust_env=false/follow_redirects=false。Bridge.scripted_response/exited设为失败，成功返回仍不接纳模拟意见或完成会议。
- 收到响应仅received_unverified，缺usage保持unknown；回执没有合成密钥/assistant正文，返回identityVerified=false，meetingCompleted/authenticityVerified=false。重复请求不会自动重发。
- 302/307/401/429/503均一次请求后unknown+halt，错误正文含合成秘密但异常trace和回执不泄漏，不跟随Location。
- 等待响应体时人工cancel、旧父Bridge120秒截止、外部任务取消均在1秒测试预算内关闭响应流并保留unknown。父时间截止通过可控时钟注入，不声称真实等待120秒；晚绑定Adapter不重置父截止。底层绝对deadline对持续缓慢body生效并关闭流。
- 空闲cancel立即终态；派发前cancel无HTTP；并发dispatch和运行中receipt被拒；已收到响应后cancel不改写已收attempt。
- 重新计算链摘要仍拒绝context/ticket/请求序号、unknown未halt、未知schema及metadata未知字段篡改。
- SystemExit/KeyboardInterrupt透传同时unknown回执仍可导出、停止且不可重试。

每个测试禁止socket.connect/create_connection和旧engine._remote/run_group。MockTransport不打开连接；密钥仅INDEPENDENT_SYNTHETIC_NOT_REAL，无读取真实凭据。

复跑：

```
PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q tests_acceptance/EXPERTREMOTE/test_independent.py research/expert_remote
```

## 限制

这是提供方边界验收，不是完整真实会议。没有DeepSeek调用、模型质量/usage/计费认证、Pi远程接通、持久化attempt账本或生产身份/案件权限。回执hash只证明局部自洽，不能证明网络确实发生、提供方身份或实际费用。单次模型名配置未在线验证。取消保留未知，不证明未发送或未计费。故意不将真实返回交给旧模拟桥接入口；未来接通须独立实现和授权。

本轮不重复140项跨模块全量回归。D01/D02修复后无当前有限提供方边界阻断；冻结终验记录另附。

## 冻结终验与裁定

新 `logs/EXPERTREMOTE-r1-impl-hashes-frozen.txt` 5/5匹配，见r1-hashes.txt。父实现者曾复用原冻结文件名写r1，独审发现后要求恢复历史文件并另立r1；恢复后的原冻结与独审首次保存的initial-hashes.txt经cmp逐字节相同，初始失败证据未丢失。原freeze仅为历史，不能对当前返工文件要求匹配。

D01、D02关闭，r1受限独立安全验收通过；23独立+58开发共81测试通过。父协调者另报142跨模块回归，不计入本独审执行计数。可按授权本地提交，不能据此宣称已完成真实提供方或远程Pi会议验收。

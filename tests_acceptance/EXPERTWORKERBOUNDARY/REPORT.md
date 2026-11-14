# EXPERTWORKERBOUNDARY 独立验收

结果：14项独立pytest通过（0.21秒），冻结3/3一致。复跑：
`PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q tests_acceptance/EXPERTWORKERBOUNDARY/test_independent.py`。

保留父f296f3d的只读内存复现：原_decode在content/id/model回显时释放合成credential，见baseline-evidence.txt。未切分支、未改运行文件；不打印合成key内容。当前独立断言包含正文、id、model、忽略字段的嵌套键/列表、JSON转义键和值，全部拒绝response_invalid且dispatched=true；异常trace不泄露合成key。无回显成功控制正常返回，身份仍未认证。

固定目标检查覆盖raw与managed模式：连语义等价的显式:443配置漂移也按字面值拒绝，在client与resolve之前失败；这不是外部URL注入测试。正常目标下managed production stub仍先拒绝。

取消在MockHTTP已经进入后触发：单次请求、task被取消、dispatched=true。Adapter独立复验回显与取消两种失败，均unknown、halted、预算modelAttempts=1、不退款、不输出responseMeta、再次dispatch失败且没有第二次请求。

测试仅合成输入与MockTransport，socket.connect禁止；不读真实凭据/环境配置、不联网模型、不改设置。Adapter测试为现有direct协议边界，不冒充真实Pi远程端到端。未独立重跑父127项，也未独立新增worker stdout测试（父已有），本次14项定位共用transport及账本。

## 限制与裁定

本防护仅检测传入程序credential在解码JSON字符串值/键中的精确连续匹配。不能检测编码变形、跨字段分片、代理未知真实key；也不是全面DLP或提供方认证。端点常量检查是配置漂移防护，不对抗能改写代码的主体。HTTP请求头仍按旧raw-key路径使用传入key；生产managed bootstrap仍不存在，真实HOLD保持。

本轮限定防护范围无阻断缺陷，可本地提交；不授权真实模型或平台设置变更。

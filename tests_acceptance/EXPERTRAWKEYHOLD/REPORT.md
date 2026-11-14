# EXPERTRAWKEYHOLD 独立验收

结果：新增16项独立pytest通过（0.11秒）；此前EXPERTWORKERBOUNDARY独审14项回归通过（0.17秒），合计实际执行30项。冻结20/20一致。证据results.txt、echo-regression.txt、hashes.txt。

复跑：`PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest --import-mode=importlib -q tests_acceptance/EXPERTRAWKEYHOLD/test_independent.py tests_acceptance/EXPERTWORKERBOUNDARY/test_independent.py`。

## 门禁及兼容

transport raw与isolated非mock在client/spawn哨兵前拒绝，dispatched=false。offline参数bool/object/MockTransport子类拒绝，managed与exact Mock混合拒绝。managed默认stub仍不可用。手工worker stdin普通模式返回raw_key_disabled无成功结果；显式--mock成功且标transportMocked/identityVerified=false。

旧engine nonfixture在packet解析/emit前拒绝，_remote无真实路径；匹配当前disclosure的CLI approved-remote仍在read_secret和创建输出目录前拒绝。Executor remote构造拒绝。Adapter direct调用失败保留not_dispatched账本、halted、不可重试，已生成账本仍可读。

显式exact MockTransport成功控制确实触发一次handler并返回public内容；合成key回显同样确实触发handler后以response_invalid/dispatched=true拒绝。因此不因raw门禁产生假绿。复核原EXPERTWORKERBOUNDARY改动仅增加离线Mock注入/适配client参数，正文/metadata/转义键值/取消/预算不退款等断言未删除，14项全部复跑通过。

历史只读兼容：使用此前保存的/tmp/mcis-connected-mock-receipt.json经完整验证转换projection，原字节未改、Mock标记与HOLD保持。该用例依赖此明确MockHTTP历史文件，不声称新执行Pi或真实模型。没有重跑全部253项或原生浏览器。

## 限制与裁定

本次禁止的是仓库现有raw调用入口，不是操作系统网络沙箱，也不对抗能改写Python代码/测试回调的主体。httpx.MockTransport的handler本身是调用者Python代码，不能据exact class声称任意handler绝无副作用；本测试使用固定离线handler并禁止socket连接。不得将真实key交给测试回调。managed仍无可信bootstrap，不具备平台代理能力。

对已知传入key的响应防护仍仅精确匹配，不覆盖编码变形/分片/代理未知真实key。未读取真实环境值、凭据或调用API，未改设置/实现/推送。限定门禁与离线兼容范围无阻断，可继续提交候选；真实运行HOLD保持。

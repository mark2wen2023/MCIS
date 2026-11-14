# EXPERTMANAGED 独立安全验收

范围：基线4dda486隔离候选，6项冻结。只新增独审文件，未改实现/环境配置，未读取真实环境变量值/密钥，未联网或调用模型。只使用公开ISRG根证书、合成配置及HTTPX MockTransport。

## 结果

24个独立pytest用例通过（0.11秒），6/6冻结一致。证据results.txt、hashes.txt、test_independent.py。复跑：

```
PYTHONPATH=. /workspace/mcis-local-export/service/.venv/bin/pytest -q tests_acceptance/EXPERTMANAGED/test_independent.py
```

- 任意引用、ready字符串/字典、错误类型等不能绕production platform_binding stub；正常形状的伪造ready元数据只能进入私有离线_validate，不能变成resolve生产授权。resolve未进入normalizer，transport未创建client，isolated未spawn worker。
- 对合成且重新pin的NO_PROXY目标后缀、通配、ALL_PROXY、SSL_CERT_DIR、大小写代理冲突、userinfo/query敏感值拒绝，异常trace不含合成秘密。
- CA父目录符号链接/FIFO/私钥拒绝且FD计数不变；合法公开CA产生CERT_REQUIRED和hostname检查启用context，Material repr脱敏。
- managed与raw key冲突在resolve之前拒绝。worker mock+managed、额外ready字段、无bootstrap生产路径均失败，不输出成功result，不建HTTPclient。
- 合成连接异常与308重定向均只尝试一次，无redirect/retry/direct fallback；固定官方POST，不应用Authorization；显式proxy和目标TLS引用同一context，trust_env=False，异常trace不泄露合成信息。

## 静态审查及限制

managed._validate要求完整精确schema、环境/运行ID与revision对应、current/ready/未撤销、有效期、固定target/method/injection合同；CA读取后摘要与SSLContext使用同一字节。isolated将Material.environment加入最小worker环境，worker重新resolve引用；Pi环境未加入此白名单。未把私有_validate的可构造元数据误认成真实性证明。

当前production platform_binding无条件拒绝是实质安全边界。离线正测中替换resolve只是测试替身，不能用于生产启用。尚无平台control-plane bootstrap、真实代理头注入/CONNECT验证、worker可信绑定传递、Executor/Adapter自动managed接线及配置摘要回执绑定；这些为明确未实现项，未来启用前必须另审。NO_PROXY不控制显式proxy路由，当前不据其做直连回退。未验证平台兼容性或真实DeepSeek能力。

裁定：本次“默认禁用、离线拟议合同”范围通过，无阻断缺陷；真实请求HOLD保持。本报告不授权删stub、手填ready、改平台配置或真实联网。

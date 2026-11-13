# 独立关闭入口：独立验收

## 结论

冻结版在本切片范围内未发现阻断性缺陷。它是独立 ASGI deny-all 占位入口，不是已经认证的业务服务。

与 `unreviewed-save/service/mcis_service` 对比，排除缓存后唯一产品变化为新增 `protected_app.py`；原 `main/create_app`、CLI 及业务实现未改。审查者未改冻结产品，只补充独立测试。

`logs/protected-entry-frozen-hashes.txt` 中产品、契约、路由清单 3 项在测试前后均 SHA-256 核验一致。

## 独立执行

命令：
`service/.venv/bin/pytest -q service/tests/test_protected_app_closed.py service/tests/test_protected_app_independent.py`

结果：**189 passed、0 skipped，2.03 秒**，原 177 项加独立 12 项。仅 Starlette/httpx 弃用警告。

原测试覆盖 154 个 method/path 清单项、文档/未知路径、HEAD/OPTIONS、伪造身份头、WebSocket、DB/旧工厂不初始化及当前 OpenAPI 清单一致性。

独立补测覆盖：
- TRACE 请求的编码路径、尾斜杠、双斜杠及查询参数均 503、不重定向；
- 原始 ASGI TRACE/CONNECT/POST/HEAD 均不调用 receive，不读取请求体或凭据，统一 no-store；HEAD 无响应体；
- lifespan 启停和 HTTP 请求均不调用旧 create_app、三种 seed、Database 初始化或 create_all；
- 原始 WebSocket 直接 close 1008，不调用 receive、不 accept。

## 实现审查

HTTP 判断独立于路由清单，所有路径统一固定 503 AUTH_NOT_CONFIGURED；不存在 enable 配置、认证解析器、默认身份、legacy fallback 或路由挂载。ASGI lifespan 仅回应启动/关闭完成，无存储副作用。错误内容不包含请求信息、路径、身份或核心错误。

## 不在本验收范围

没有登录、subject/session、案件成员权限、真实身份提供方、事务授权、可用业务路由或调查员工作流。没有浏览器、GitHub CI、生产服务器、代理、隧道、端口或网络隔离验证。

这个应用不能保护另一个仍运行的旧进程。旧 CLI/应用仍使用可伪造角色头；本测试不能据此宣称旧服务已具备认证或已经安全接入内网。运行入口选择和实际网络隔离仍需后续单独核实。

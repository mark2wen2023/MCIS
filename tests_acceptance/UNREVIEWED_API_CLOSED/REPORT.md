# 未审核保存 HTTP 安全前置：独立核验

结论：当前交付保持关闭是正确边界。仅新增设计契约和关闭状态测试，不是 HTTP 新功能，也不代表认证完成。

- 已阅读 `contracts/unreviewed-api-design.md`：明确 legacy X-MCIS 头不是真实认证；要求未来逐案件授权、初始/最终事务复核、幂等重放前复核；不伪称外部身份库具备跨数据库原子性。
- 对比 `../unreviewed-save/service/mcis_service` 与当前产品实现，排除 `__pycache__` 后没有差异。没有新增可安装 builder、默认路由、设置开关或授权 callback。
- 独立执行原 5 项：5 passed、0 skipped，2.74 秒。
- 新增 3 项独立无身份头 GET/POST/PUT 请求，均 404，全部数据库表快照不变。
- 合并执行原测试及 `test_unreviewed_api_closed_independent.py`：**8 passed、0 skipped，3.23 秒**，仅 Starlette/httpx 弃用警告。
- 默认 OpenAPI 不含 unreviewed-runs；伪造四种 X-MCIS 角色头不能启用保存接口。

未来真实身份解析、CSRF/Origin、案件成员资格、会话有效性与最终写入授权的事务关系仍需设计及独立验收。没有 UI、认证集成、HTTP 保存接口、生产部署、浏览器或 CI 验证。本报告不能用于声称调查员已可通过网页保存结果。

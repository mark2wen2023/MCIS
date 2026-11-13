# 内部未审核结果保存：独立审查与验收

## 最终结论

冻结版本未发现剩余本切片阻断性缺陷。通过的是内部服务端计算、事务保存、受限幂等重放及支持范围内历史往返，不是用户可见保存功能、人工审批或生产上线验收。

审查者未修改产品实现，新增独立测试 7 项。`logs/internal-unreviewed-save-impl-hashes-frozen.txt` 中 8 个实现/契约文件在测试前后均 SHA-256 核验一致。

## 首轮独立发现与修复

独立复现：操作人含 U+2028 时 `save_unreviewed` 返回 saved=true，但之后完整导出报 409 ARCHIVE_RESTORE_UNSUPPORTED。原因是审计物理行保留 Unicode 行分隔符，现代包解析器拒绝，旧读取器可能拆行。

实现线程已在计算和写入之前拒绝 U+0085/U+2028/U+2029 以及 UTF-8 孤立 surrogate。独立补测确认均 422，未调用核心，数据库完全不变。原 operator/role 也已冻结，不随外部 context 对象在计算期间变化。

## 独立执行结果

命令：
`MCIS_PREFLIGHT_REAL_CORE=/tmp/mcis-preflight-core.sh service/.venv/bin/pytest -q service/tests/test_internal_unreviewed_save.py service/tests/test_internal_unreviewed_save_independent.py`

结果：**32 passed、0 skipped，16.85 秒**，包含原 25 项和独立 7 项。1 项运行实际 W2 核心，其余使用模拟核心或直接验证状态。只有 Starlette/httpx 弃用警告。

独立新增覆盖：
- 4 类不可安全归档 actor 的前置拒绝及无副作用；
- 两个 fixture 角色都具有完整内容权限时，同 operationId 更换 role 仍 409，不重算、不重放；
- index.operation_id 或 index.run_id 被改写时失败关闭，不修复、不重算、不新增数据。

基础测试覆盖：真实 SQLite 保存；同 scope/当前版本重放；不同请求/操作者/权限/原件状态拒绝；并发同 key 的单胜者及不同请求冲突；审计追加后、index flush、commit、容量错误回滚；提交后丢弃响应再次取得同 run；支持的导出/恢复/再次导出保留完整历史但不建立活跃 index；恢复后新原件可使用同历史 operationId 产生新本地 run。

## 审查确认

- 初始和最终短保留写事务检查完整内容及 timeline 写权限，核心在事务外运行。
- 最终事务直接写完整 audit marker 和 index，不接受客户端结果封套，不把已返回的 preflight 当写凭证。
- 重放验证 index、完整 marker、原身份作用域、审计链和当前案件/来源/父报告快照。缺 index 的当前代次 marker 不能触发第二次保存。
- 数据库唯一约束限制 operation 作用域、runId 和 auditSeq 关联。
- 审计完整 escaped UTF-8 容量检查发生于 commit 之前，异常回滚审计与 index；返回成功发生于 commit 后。
- 历史恢复保留 operationId 但不激活重放；处理协议版本有记录，核心实现版本明确 `not_attested`，不伪称二进制版本已认证。

## 限制

没有 HTTP 保存入口、列表/历史 UI、人工审批、生产身份认证或部署。完整内容 gate 是保守门禁：默认 Investigator 的医疗/PII 限制会先拒绝，不代表本切片授予普通调查员新的访问权限。

实际 W2 仅 1 个正向保存样例，不代表所有数值或调查业务场景经过验证；其余核心替身测试只证明边界与事务行为。没有真实 LLM、浏览器或 GitHub CI 验证。并发测试为同进程独立线程/会话，不是多进程压力测试。故障注入不等于断电/进程崩溃 ACID 证明。

64 KiB 归档余量是有限预算，不保证无限后续审计增长。历史 marker 仍是未审核声明，不证明调查事实、抽取关系或责任判断。非默认权限策略的现代归档恢复限制仍按既有行为保留。

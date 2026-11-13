# 同库身份授权内核：独立验收

## 结论与范围

修正后的本切片未发现剩余阻断项。实现是可调用的本地身份/会话/成员资格授权内核及内部未审核结果保存入口，不是完整HTTP身份系统、登录、IdP、内网部署或调查员可用的完整工作流。

审查者未修改产品文件，只添加 `service/tests/test_local_authority_independent.py`。产品校验值见同目录 REVIEWED_SHA256.txt。

## 独立发现与修复复验

初版 `authorize_save` 接收已存在的显式 deferred BEGIN，未证明 SQLite writer reservation 即返回 Authority。独立首次运行 4 passed / 1 failed 复现该问题。实现者增加当前 transaction、connection、线程及底层事务状态证明检查后，该测试通过；旧事务证明也不能跨commit复用。

## 实际执行

- 主测试28项 + 当时独立12项：40 passed，0 skipped。
- 最终独立13项：13 passed，0 skipped，7.98秒（与上一条重叠，不相加）。
- 独立测试使用真实临时SQLite/API夹具，计算输出受控模拟，不是新增真实W2/LLM验收。

覆盖：
- 同subject新有效session可合法重放，旧撤销session拒绝；另一subject不能复用operation。
- 实际线程并发：核心计算期间另一线程撤销提交，最终403且无新增结果/审计。
- 实际线程并发：保留授权事务持锁期间另一线程撤销不能提交；原事务结束后撤销提交、后续授权拒绝。
- token仅持久化SHA256；provisioning异常整个事务回滚。
- 成员资格caseId或case incarnation不匹配均拒绝。
- 初始capture、重放capture、最终capture期间会话到期均拒绝，无额外写入。
- 重新执行主测试包含完整export→新空库restore，三授权表均为空、旧token不生效。

## 归档审查

新增三个 identity_local_* 表只加入明确的 GLOBALS 排除名单，避免闭世界归档因部署本地身份数据而阻断。归档构造与导入仍使用显式业务字段，不使用表名驱动通用恢复，因此不将本地subject/session/membership序列化或还原。历史审计可保留actor标识，但不是授权。

## 限制

本地provision函数需受信host管理员调用，无外部管理端认证。既有旧应用仍相信角色头；新内核不保护继续暴露的旧应用。protected_app仍统一关闭，无公开启用开关。不存在默认管理员或自动授权。未验证浏览器、CI、真实IdP、生产网络或整库回滚/时钟回拨防护；未合并、未部署。

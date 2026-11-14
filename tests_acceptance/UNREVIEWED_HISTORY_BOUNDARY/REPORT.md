# 未审核历史访问/容量前置：独立审查

## 最终结论：前置边界通过独立复验

首轮静态审查发现并通过 TestClient 独立复现访问工作台旁路，开发线程已修复并补测。最终冻结版本独立复验未发现本切片阻断性缺陷。审查者未修改产品实现，仅新增独立测试。该结论不是结果持久化或完整保存闭环验收。

### 已修复：access-workbench 曾返回未授权完整 marker

复现场景：通过合成历史行构造 `category=Access`、`action=policy.update`、`entity_type=accessPolicy`、`entity_id=policy`，`snapshot_ref=local-unreviewed-result:v1:<synthetic content>`。随后将 Investigator 的 audit 设为 ReadOnly、evidence_meta 设为 Deny。

修复前独立观测：
- `GET /audit`：403，不含合成内容。
- `GET /access-workbench`：200，`policyAudit.events` 中含完整合成内容。

原因：访问工作台直接返回 `audit.list_events` 结果，只调用 recommendation guard，未接入 unreviewed guard。历史导入可持有这种分类与 marker 组合，不能依赖未来保存端点只写标准分类来排除。

最终版本已在 access-workbench 接入同一 unreviewed guard。精确旁路回归已通过，独立追加 timeline/testimony 为 Redacted 的双入口测试亦均返回 403、不含内容；LeadInvestigator 仍可读取，未关联普通工作台保持 200。

## 归档失败定位

独立复现 modern package-intake 恢复后的重导出失败，结论与新 guard 无关：恢复后 `deny_evidence` 将权限策略改为非默认，`parse_package` 拒绝并报 `PACKAGE_INTAKE_INVALID: 仅支持默认权限策略`，外层映射 `ARCHIVE_RESTORE_UNSUPPORTED` 409。

对照结果：
- 不含 marker、修改策略后：409。
- 含 marker、修改策略后：409。
- 不含 marker、保持默认策略：200。
- 含 marker、保持默认策略：200。

应将完整重导出验证放在默认策略条件下，随后单独验证撤权后的读取/导出拒绝；不得将现有非默认策略恢复能力写成已完成，也不应绕过恢复预检。

## 其他审查

- 当前审计主入口的投影字段/原始行双路径识别、防重复键及非有限 JSON 处理方向正确。
- 完整内容门禁比逐来源门禁保守，但保护导入历史无 index 的情形是合理的，可能拒绝具有部分权限的调查员，需如实描述。
- 容量 helper 按实际 UTF-8 审计字符串及换行计算，64 KiB 只是有限余量，不能保证无限后续审计增长。
- 容量 helper 尚无保存调用者：目前不提供任何持久化容量保证。
- 本轮为本地静态审查/TestClient 复现，没有 CI、浏览器、真实 LLM 或部署验证。


## 冻结版独立执行结果

- `sha256sum -c logs/unreviewed-history-boundary-impl-hashes-frozen.txt`：4 个实现文件和 1 个设计契约全部 OK，测试后复核一致。
- `service/.venv/bin/pytest -q service/tests/test_unreviewed_history_boundary.py`：**17 passed、0 skipped，4.43 秒**。
- `service/.venv/bin/pytest -q service/tests/test_unreviewed_history_boundary_independent.py`：**5 passed、0 skipped，2.56 秒**。
- 独立补测覆盖未知 marker 版本、timeline/testimony Redacted、审计主入口/访问工作台两个出口，以及无关联工作台兼容性。
- 两轮仅出现 Starlette/httpx 弃用警告，无测试失败。

最终归档测试明确区分：现代入口默认策略下历史保留重导出成功；改为非默认策略后保留既有 409 拒绝。旧入口仅使用无 working 扩展的支持范围 fixture，不宣称它能恢复 working 扩展。

容量校验仍只是尚未接入保存调用者的前置 helper。严格封套 schema、导入语义校验、保存事务、index、审批和历史 UI 均未在本切片实现。

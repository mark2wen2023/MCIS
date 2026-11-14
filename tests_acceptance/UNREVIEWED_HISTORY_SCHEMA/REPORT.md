# 严格未审核历史声明：独立验收

## 最终结论

冻结版在本切片范围内未发现剩余阻断性缺陷。审查者未修改实现，仅新增独立测试。通过的是历史声明严格结构、内部关联和导入前置验证，不是历史真实性认证、结果保存或人工审批闭环。

冻结核验：`sha256sum -c logs/unreviewed-history-schema-impl-hashes-frozen.txt` 中 3 个实现文件、JSON Schema 及契约说明全部 OK，测试后再次核验一致。

## 独立发现与修复复验

首轮独立复现以下错误声明被接受：
- 外层 case 正确、`serverPreview.result.caseId` 指向其他案件；
- 内层可选 result epoch 与外层快照不一致；
- `version=1.0` 以及 `registeredSeq=1.0` 未被 JSON Schema 的 integer 类型拒绝。

实现线程已补充内外 case/epoch、每个 conflict case 检查及显式严格整数检查。独立复跑确认拒绝。随后补充与 preflight 一致的 Error 导入诊断拒绝、不同来源登记序号唯一性。最后新增的转义孤立 surrogate 拒绝修正也纳入本次最终重跑。

旧导入校验位置已确认：在已有审计链校验后，在本地代次分配、业务 SQL 和 blob 写入之前。不是在审计行写入前才晚拒绝。

## 独立执行

命令：
`service/.venv/bin/pytest -q service/tests/test_unreviewed_history_schema.py service/tests/test_unreviewed_history_schema_independent.py`

结果：**47 passed、0 skipped，9.36 秒**，包括实现线程的 35 项测试及审查者独立新增的 12 项。仅有 Starlette/httpx 弃用警告。

独立新增覆盖：
- NaN、正负 Infinity、浮点溢出 `1e999` 拒绝；
- 保留 category/action/entity/未来版本 namespace 缺少规范 marker 时拒绝；
- identity version 与 snapshot byteLength 的浮点整数拒绝；
- 含实际供写入 raw blob 的坏包在旧入口被拒，数据库和文件均不产生副作用；
- 两来源合法声明正例成立后，重复登记序号拒绝；
- 两来源合法冲突正例成立后，跨案件 conflict 被拒。

基础测试还覆盖两导入入口损坏版本/缺失/影子字段/重复 runId 的早拒绝、有效声明精确保留并再导出、恢复后不产生本地 unreviewed 表、额外字段和假审批拒绝、深度/容量预算及普通旧审计兼容。

## 边界

有效声明仅表示格式和自报关系一致，历史 UUID、SHA、登记编号、模型输出不能证明实际来源或事实正确。恢复不生成本地 index、不激活结果、不授予任何批准权。

本切片没有新增保存 API、index、保存事务、审批、历史 UI 或完整归档容量保证。旧入口仅在其既有支持包范围测试；不宣称旧入口支持 working-records 扩展。现代入口非默认权限策略恢复/重导出仍有既有限制。

以上为本地 Python/TestClient/SQLite 合成历史测试，没有 CI、浏览器、实际 W2 运算、真实 LLM、生产部署或崩溃/断电验收。此测试使用的历史结果 fixture 明确为合成自报声明，不冒充真实计算记录。

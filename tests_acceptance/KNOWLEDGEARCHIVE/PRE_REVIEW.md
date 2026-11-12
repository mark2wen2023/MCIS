# 知识归档合同预审及 B OpenAPI 文档补正检查

## 知识归档合同

设计预审通过，未裁定实现通过。当前全局卡/原审计能完整保存；旧 Withdrawn 覆盖的审批不可重建，合同明确不回填。新 create/review 原子完整 before/after 快照与 epoch、旧原行 SHA 关联、严格覆盖连续性、只读独立历史、不激活在线 Published、Lead 全入口门禁、原包 BLOB 完整取回及预算均已定义。案件归档只排除明确的三个新全局表，仍须测试未知非空表拒绝。

实施核对点：深度 32 的计数定义保持测试一致；所有 summary/list 均实现 §9 新增快照计数和覆盖字段；完整 doc 校验不可误用仅针对 content 的 32 KiB 限制。上述不是放宽合同，也不是已有功能完成声明。

## B 文档补正

独立重跑 `service/tests/test_knowledge_w192.py::test_route_contract_without_real_seeds`：**1 passed / 0.47 秒**。测试使用无真实种子的应用，所有声明路径/方法与实际 API 匹配。

另用两个独立临时合成数据库，通过真实 FastAPI TestClient 生成归档并恢复。interview/report 两种 provenance 实际 200 JSON 均通过新增 OpenAPI 3.1 JSON Schema 校验；历史原件实际下载字节与合成原文一致，Content-Type、attachment、X-Sha256、no-store 与声明匹配。检查业务 router 和 fragment 字段/路径一致。仅文档补正检查，不声称重新运行 Archive B 全部验收或浏览器。

未改业务代码。API route 测试有框架 TestClient 弃用提示，不是失败。

## 本次读取文档 SHA-256

- `contracts/openapi.yaml`: `ab4ed8118fd3fbe6d079c8efff63636d162dc7c09a33776625d3061917dfd40e`
- `contracts/working-record-archive-api-fragment.md`: `8c6e6d1099dcbe5a4909946b7cfbd939ec9c7f1f5e379a6f01b765468efad18d`
- `contracts/knowledge-archive-v1.md`: `c4bfb3a1c75de72d87874c46c78a519b14be49abae68c23f37276bfc29261524`

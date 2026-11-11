W16 已实现：三模板×三语言、句子级引用、人工复核、版本保留、PDF/DOCX、术语表、GISIS，以及 `#/report` 页面。真实案例保持“待确认”。

**文件清单**

- 新增 `service/mcis_service/reports/{__init__,models,templates,sources,service,router,gisis,exporter}.py`。
- 新增 `service/tests/test_reports_w16{,_direct,_sources,_export}.py`。
- 新增 `web/src/reports/{types.ts,api.ts,ReportView.tsx,ColregDraftButton.tsx}`、`web/src/pages/ReportPage.tsx`、`web/tests/report-render.test.tsx`。
- 新增 [report.schema.json](/workspace/maritime-sim-design/contracts/schemas/report.schema.json)。
- 最小追加修改：服务 `main.py`、`requirements.txt`；网页 `routes.ts`、`main.tsx`、`package.json`、`styles.css`；`contracts/openapi.yaml`、`REQUESTS.md`。

**接口清单**

全局前缀 `/api/v1`：

- `GET /report-templates`
- `GET /report-glossary`

以下以 `/api/v1/cases/{caseId}` 为前缀：

- `GET/POST /reports`
- `GET /reports/{reportId}`
- `POST /reports/{reportId}:generate`
- `PATCH /reports/{reportId}/sections/{sectionId}`，支持可选 `sentenceId`
- `GET /reports/{reportId}/audit`
- `GET /reports/{reportId}/export`
- `POST /reports/sections/colreg:draft`
- `GET /gisis`
- `POST /gisis:validate`
- `GET /gisis/export`

**新增错误码**

- 409：`report_real_data_pending`
- 404：`report_not_found`、`report_section_not_found`、`report_sentence_not_found`
- 422：`report_invalid_argument`、`report_review_reason_required`、`report_review_no_change`、`report_review_field_not_allowed`、`report_review_text_required`、`report_gisis_validation_failed`
- GISIS 字段校验返回 `field_*` 明细。

**测试结果**

- 无 socket 的 W16 测试、schema 合法性及 W16 路由核对：**72 项通过**。
- `npm run test:w16`：**111 条断言通过**。
- TypeScript 检查：通过。
- `test_reports_w16.py` 的 **41 项 HTTP 测试**已保留；当前沙箱 TestClient 挂起，40 秒超时，需外部运行。
- 全局路由一致性最后一次失败：并发新增的 **5 条 W6.1 路径**尚被 `PENDING_CONTRACT=True` 隐藏。W16 的 13 个操作一致。

[REQUESTS.md](/workspace/maritime-sim-design/REQUESTS.md:172) 已记录接口、schema、复核规则、完整审计、版本与真实数据门禁，并补充验证结果。

需外部整合或 Gemini 裁定：GISIS 正式字段映射、W14/W15 来源合同、中文模板正式名称、审计扩展和 W17 报告脱敏；W6 独立按钮接线、Layout 顶栏案件同步及上述 W6.1 合同同步。当前报告业务入口限定调查员角色。
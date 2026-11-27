# W12 同案轨迹换版接线核查

底版 `94d5e38c926fda232bb987b60fa9145e4bcf01a7`；分析快照针 `03a8e7867fedbaaabbf8dd12fc9041d6a1a74cd5`。独立候选 `candidate/w12-track-version-wiring`。本目录只新增文档，不改产品接口、算法、契约或权限。不重跑跨案、等候帧或窄屏布局。未启动服务、未跑 HTTP、未跑浏览器。

## 结论

没有现成「同案轨迹换版」API，分析接口仍返回离线 `seedSha256`，不能读出当前登记航迹版本。首个断点见 `IMPLEMENTATION.md`。可执行验收条件见 `ACCEPTANCE.md`。

既有只读入口 `GET /api/v1/cases/{case_id}/track-imports?vesselId=` 与 `GET .../track-imports/{digest}` 能输出首次导入身份（`caseId` / `vesselId` / `previewDigest` / `sourceSha256` / `reportSha256`），但分析未消费；合同为「首次保存且不支持后续编辑」，同船第二版会被 `TRACK_EXISTS` 拒绝。归档历史为 `archive-only`，不是当前活跃版本。

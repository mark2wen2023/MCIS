# W17.1 权限与脱敏：只读核验切片

## 依据与边界（2026-11-12核对）
- 原设计：ROADMAP W17 / ARCHITECTURE ⑭，现有 access-policy.schema.json、audit-event.schema.json。
- [IMO MSC.255(84)](https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MSCResolutions/MSC.255%2884%29.pdf)，第三部分建议做法22.2及23.1–23.3：调查证据应防止无调查需要者访问，披露需考虑安全调查目的及相关性。这是设计依据，不是本系统已经法律合规的结论，也不把项目矩阵说成IMO逐项规定。
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)：默认拒绝、每次请求验证权限、对授权逻辑做测试。对应本切片服务器端逐案检查、失败无详情、身份变化清除旧结果和负向测试；不声称本地角色头已具备身份认证。

## 范围
17号工作台从占位页变为当前案件真实配置只读视图：角色/资料类别矩阵、当前自报角色、字段规则、策略来源、最近策略变更记录。无编辑/保存/授权/导出/脱敏预览功能，不读原始笔录或证据内容。
矩阵和字段规则仅表示配置，不能据此宣称所有规则已在全系统实施或敏感字段已全部消除。审计空态不等于从未发生变更；只展示已记录匹配事件。
不改旧access-policy或redaction接口，不碰W11；不部署，不增加认证、加密、LLM或外部数据发送。

## 接口
GET `/api/v1/cases/{case_id}/access-workbench`
- 每次仅允许Investigator/LeadInvestigator，且该案件audit值为ReadOnly/ReadWrite。其他身份、Deny/Redacted/未知/缺失权限统一403，不附策略、记录、案情。
- 无权请求不泄露案件是否存在；有权且案件不存在404。
- 200：`{caseId,policy,policySource:'default'|'saved',policyAudit:{events,limit:50,hasMore},identityMode:'local-role-header',readOnly:true}`。
- policy沿用access-policy schema。不存在保存行时返回默认策略并明确default；不得为读取落盘默认策略。
- events沿用audit-event schema，只匹配当前案件category=Access、action=policy.update、entityType=accessPolicy、entityId=policy，seq倒序最近50；取51判断hasMore。无伪造、无自动补审计、无自动创建案件。
- 单一数据库读事务获得策略和历史；GET不改变业务状态。

## UI验收
明确显示“本地自报角色，不是真实身份认证”和“只读核验”；不得把role切换当登录或权限授予。
案件/身份切换立即清除旧数据，终止旧GET并用世代检查拒绝迟到响应；失败、空态、无案、403、默认来源有明确文字。
不以浏览器隐藏代替服务器授权；只请求新端点，不回退旧无角色限制策略端点。
未知类别/角色展示原标识，缺失矩阵项显示默认拒绝，不伪装已配置；声明与实施效果明确区分。
独立测试覆盖无写入、权限/策略变化、跨案件隔离、审计过滤/50边界、错误、真实浏览器及迟到响应。

成功与403响应Cache-Control:no-store；前端GET亦cache:no-store。SQLite在首次SELECT前显式BEGIN，只限该新端点，避免策略与变更历史混合快照；普通读取不写数据。

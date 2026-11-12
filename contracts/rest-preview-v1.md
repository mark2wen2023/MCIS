# W18.3 工休基线技术预览（非合规结论）

## 官方依据核对与未决事项（2026-11-12）
- [IMO 2010 Manila amendments STCW/CONF.2/34](https://wwwcdn.imo.org/localresources/en/OurWork/HumanElement/Documents/34.pdf)，A-VIII/1第2–3段（PDF219页）：值班/指定安全等职责人员一般休息基线10h/任意24h、77h/任意7d，分段不超过2段，其中一段至少6h，间隔不超过14h。第4、6、8、9段另有紧急/特殊作业、补休及授权例外。此为所核对版本来源，不代替船旗国适用法、职位适用性和具体授权核查。
- [ILO MLC 2006含2022修正的合并文本](https://www.ilo.org/sites/default/files/2024-10/NORMES_MLC%20Amendments-EN_2022_Web_1.pdf)，A2.3第2/5段是最长工作或最短休息两种体系；不能自动把72h工作上限与77h休息下限同时作为必适用规则。第1段休息不含短暂休息，第13/14段有授权例外与紧急工作。本切片不判断这些条件。
- 原项目W18.2已验收的RestHours.cs是唯一计算源。直接WorkRestSchedule.Create，不使用FromWork/FromRest补集。固定ApplyWorkHourLimits=false，只作普通休息基线预览，不允许用户改阈值。
- 既有“完整休息段对齐窗口”拆分算法是项目假设，不是已证明与法律原文等价。原假设完整展示；滚动/拆分/间隔输出仅作为技术核查线索。
- 核心在记录短于24h/7d时跳过相应滚动规则；适配器必须单独明确coverage，空findings绝不能显示“合规”。不评估疲劳诊断、HFACS确认、BRM、责任或事故因果，不写入已确认事实。

## 真实业务范围
13号页：选择当前案件已登记证据作为参考，人工按来源转录UTC工休时段并请求一次非持久化本地技术计算。无自动填入真实人员结论；演示/验收仅合成资料。
来源返回只表明当前案件的登记元数据快照，不重新核验原件字节、不证明人工时段与原件一致、不把登记即当真实性证明。短暂间歇不能未经专业核对自动标为Rest；Unknown不是Rest。

## 输入与接口
GET `/api/v1/cases/{case_id}/human-factors/rest:sources`
返回 `{profile:'MCIS-REST-PREVIEW-1',caseId,sources:[{evidenceId,title,sha256}],sourceBinding:'registered-metadata-only'}`。
POST `/api/v1/cases/{case_id}/human-factors/rest:preview`，严格JSON（128KiB，不接收重复/未知键、NaN/Infinity）：
`{recordStartUtc,recordEndUtc,intervals:[{startUtc,endUtc,kind}],sourceEvidenceIds:[...]}`。
UTC秒格式YYYY-MM-DDTHH:mm:ssZ；kind=Watch/OtherWork/Rest；区间半开，首尾相接允许、重叠/越界/零长拒绝。
工程限额：1900–2100年、记录>0且<=14d、1..256区间、1..8不重复来源ID。限额不是专业阈值。
来源须属于当前案且可完整读取，哈希有效；无来源不能计算，不允许任意新ID、跨案来源或客户端替换登记hash。
调查组角色且该案personal、evidence_meta均完整可读（ReadOnly/ReadWrite）才允许；按既有保密可见规则过滤，不泄露拒绝对象。角色头是本地自报，不是认证。
计算结束前复核权限及所选登记快照；变化则403/409，不返回过期结果。GET/POST不改DB、证据、审计或策略；no-store，不发送外部LLM。

## 输出
`{profile:'MCIS-REST-PREVIEW-1',caseId,inputSha256,sources,sourceBinding:'registered-metadata-only',persisted:false,assessment:'technical-preview-only',result,limitations:[...]}`。
inputSha256绑定规范化输入、当前案和服务器登记来源快照，提供可比对的请求出处，不宣称身份签名。
独立mcis-rest CLI直接引用不变RestHours.cs，独立可复现构建及来源清单，不改变原mcis-core DLL/W12来源或W11。
result: coreVersion='mcis-rest/1',mode='rest-baseline-no-exceptions',totals={restHours,workHours,unknownHours},coverage={recordHours,has24hWindow,has7dWindow,unknownHours},findings,insufficientData,assumptions。
findings/insufficientData每项rule/windowStartUtc/windowEndUtc/actualHours/limitHours/violatingFromUtc/violatingToUtc/clause/detail。
rule仅Rest24h/Rest7d/RestSplit/LongestRest/RestInterval；数值小时，原核心假设与窗口边界保留。无isCompliant/“通过合规”结论；记录覆盖不足或Unknown必须突出。未发现偏差也不能排除例外适用、原始数据错误或算法假设问题。
核心不可用明确503，无Python重算/假结果替代。核心错误、超时、超限响应安全失败。固定输入不注入命令或CLI路径。

## 验收
合成数据：10h/77h边界、缺24h/7d窗口、未知间隙、重复/重叠/越界/UTC非法、证据跨案/不可见/变化、权限撤销、不产生写入、未配置核心、并发构建、原核心hash不漂移。
UI显示来源声明/固定规则/未评估事项，空表单不预先确认资料；编辑、换案、换身份使旧结果失效；明确仅技术预览、不保存。
独立真实CLI+API+浏览器验证，测试仅合成资料，不以未知记录或空结果断言合规。

实现细化：人工区间按开始时间升序提交；不自动重排记录。RestSplit输出actualHours是最长两段的合计时长，limitHours是10小时，不是“2段”的段数。界面需重算case+完整输入+用户所选登记快照的规范化SHA，且逐项核对来源id/title/sha；不一致只提示刷新，不显示旧结果。计算完成前的服务端来源/政策复核不能替代此浏览器绑定检查。

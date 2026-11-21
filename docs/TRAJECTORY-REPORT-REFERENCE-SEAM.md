# 轨迹报告引用：内部接缝提案（未实现、不可保存）

固定依据：轨迹候选 **afc72a1180ae345556a85fb63a4020a476893d14**（T），报告候选 **94014643c02a1dd046ee8b0bfb76ae3b36631509**（R）。本分支以T为父，仅加本文，未组合R代码。不是共享轨迹V1合同修改，不提供可执行schema、授权器、路由、存储或默认入口。

## 真实边界对照

以下路径相对 `service/mcis_service/`，行号属于固定提交。

|固定来源、方法|已有保障|不能据此声称|
|---|---|---|
|T `common/context.py:27–35 get_ctx`|旧单机角色/操作者上下文|从请求头和默认Investigator构造，不是服务器认证身份，也不是report grant|
|T `evidence_intake/router.py:220–233 _read_original_for_access`|先authorize，再load_receipt，protect_container，追加Access；沿原下载读取路径|不是认证器；调用者负责可信上下文、访问目的与事务|
|T `trajectory_exchange/registered_pair.py:34–85 _read_registered_pair`|同案两固定pin，逐份真实读取、回执逐字段一致、原字节SHA与V1、不同船检查；无半成品返回|仅共用session不等于跨组件授权闭环；失败须由外层回滚，不能在事务内吞异常|
|T 同文件104–124 `_load_registered_pair`|WRITE_LOCK + Database.session + reports.access.begin；commit/close成功后才返回|该事务已结束；不能把返回批次当随后报告写入的同一视图或长期权限|
|T `trajectory_exchange/registered_query.py:12–34 _query_registered_pair`|每次重读固定原件；提交后的纯投影；不读latest|不能直接拿UI回传的投影或旧缓存创建报告绑定|
|T 同文件37–66 `_point_from_committed_original`|复用精确UTC/缺口优先选择；生成JSON Pointer，保留recorded/interpolated和缺HDG|是私有投影，不是可信快照或权限对象；不能绕过读路径直接对客户端JSON调用|
|R `reports/access.py:15–23 begin`、30–62 `require_content`|SQLite首次读取前BEGIN IMMEDIATE；角色、全类别读取、fieldRules及写入report_draft限制|不建立登录主体；不替代逐原件授权、容器/历史检查，也不解决跨进程撤权问题|
|R `reports/router.py:29–40 check_access`|完整报告检查、案件存在/可用及report_draft；131–135快照还需audit权限|把角色传入即可调用不等于可信服务端report grant；不能降低成单一case.read|
|R `reports/generation_snapshot.py:15–74 generation_sentence`|完整生成/再生成RA及审计关联、同案报告、唯一段/句、family/version约束|不校验审计链真实性、不授权、不持久化；可编辑当前报告不是冻结来源|
|R `reports/sentence_binding.py:172–213 prepare_audio_binding`|要求BindingReadScope、固定生成句、media=audio、精确旧音频读取与既有SHA|不接受轨迹定位；不得伪造run/revision/segment；没有生产BindingReadScope实现|
|R `reports/sentence_binding_store.py`|显式opt-in、调用方session、唯一键与只追加、外键关联RA|低层存储不认证载荷；现有audio envelope不容纳轨迹；不得直接put_doc或调用低层insert伪装报告绑定|

R的报告读取92–98、快照131–135、导出139–152各有既有保护，但没有本提案的轨迹引用钩子。T/R尚未组合；同名access方法也须在将来固定组合上重新核对，不能仅凭函数名认定等价。

## 拟议内部类型（只用于后续审查）

类型名暂定 `frozen-sentence-trajectory-reference/1`，不是现有可接受的存储格式。首版每个冻结句仅一个证据对象；若需双船结论，必须另行设计多证据绑定，不隐式丢掉另一船。

- 唯一键：`(caseId, generationSnapshotId, sectionId, sentenceId)`；generationSnapshotId必须是实际服务器读取的 `RA-` 加32位小写hex；段/句必须经完整生成快照唯一定位。
- 不变报告身份：`auditSeq, reportId, familyId, version`，均从 `generation_sentence` 结果取得，非客户端赋值。另保存冻结句规范化摘要，不复制正文、引文列表、来源说明或摘录；新的摘要编码方案需独立冻结并设大小/深度界限，**本提案不更改旧音频SHA配方**。
- 不变原件身份：`caseId, evidenceId, requestDigest, sourceSha256, vesselId`。前四项须与同案真实登记回执逐项相等；vesselId来自经V1校验的原文字节。requestDigest是登记请求摘要，不是原件SHA、轨迹修订号或报告摘要。sourceSha256是原始字节SHA-256，不是重序列化JSON的SHA。
- 查询定位：`alignedUtc`、`kind` 和服务器选择器生成的 `jsonPointer`。UTC必须通过当前精确查询输入校验；新绑定规范为毫秒精度UTC Z字符串，同一时刻的秒精度输入只能由服务器规范化，不能改变被定位的原记录或既有返回值。
- `kind=source_sample`：只允许精确匹配已有 `/points/<index>`；保留 `positionKind=recorded|interpolated`。interpolated是原件已有插值，不称实测或本轮重新插值；只有经现有V1验证可同步的记录才可定位。可保留本行已验证的 sourceUtc/correctionSeconds/status 作为内部核对字段，但每次必须对原字节重算比对。未知HDG仍未知，不从COG补造。
- `kind=declared_gap`：只允许选择器实际返回的 `/sampling/missingIntervals/<index>`，保存原件声明的startUtc/endUtc；查询时刻严格处于开区间内部。它是“原件声明缺轨”的引用，**不是轨迹点**，不带位置、艏向、碰撞角；端点由既有精确点选择规则处理，不能自己改变开闭区间。
- `no_observation_at_time`：无对应记录，不生成引用/指针；不能找最近点或沿用上一点。状态可向已授权调用者报告为不可绑定，但不能写成假引用。缺轨有明确原文声明才与此不同。

字段、类型和允许键须严格；未知键/重复键/非法值/过深/超大输入拒绝。这里只列设计，不引入一个可由任意JSON“验证后即可信”的函数。标识、时间和摘要本身也属受保护内部数据，不是display/API对象。

## 原字节与服务器定位必须同时成立

沿T既有路径读取每份登记原件，保留authorize、load_receipt完整性/历史处理、容器保护、Access与审计。两份pin由可信服务端选择，不接受浏览器pin证明授权。

1. 回执与固定pin精确相等；原件必须bytes且≤4MiB，SHA-256等于sourceSha256。禁止对解码后JSON重编码替代原字节摘要。
2. UTF-8解析拒绝重复键/非有限值，沿既有V1校验、同案/不同船/可同步判断；未知时间不参与定位。
3. 复用已有选择器语义，从上述已验证原件生成pointer；index存在且所指记录的时间、类型、坐标/缺口与提案相同。pointer字符串本身或SHA相同都不是权限证明。
4. 持久化最小字段和摘要；不复制原始整行或坐标全文进报告绑定。若需字段摘要，必须先冻结规范化配方，再证明固定同一pin但定位/类型/UTC改变会冲突；不要借用audio referenceSha256名称暗示兼容。

## 保存、重开和错误状态（尚未接线）

|情况|所需结果|
|---|---|
|无可信服务器主体/report grant|在读取报告/轨迹或写入前拒绝；不能用默认角色或测试Ctx替代|
|同案完整生成RA、双方许可、精确记录成立|才可准备提案；尚不是保存成功|
|同key、整个规范载荷相同|在原子存储约束下幂等；相同不等于授权|
|同key任一身份、句摘要、pin、UTC、pointer、类型改变|冲突，不覆盖；新生成RA独立|
|历史确无绑定|明确无历史引用，不猜旧版本|
|有绑定但格式损坏/原件缺失/SHA不符/授权失败|明确不可用；不能降级成“无引用”或latest|
|无精确行|不生成引用；不得把未知变成零|
|重开|重新判报告/快照audit及每份原件访问，再核旧pin/原字节/句；不得用旧批次缓存授权|
|任一读取、写入或提交异常|不返回成功；回滚责任由外层事务；提交异常不证明未提交，不自动重试|

未来真正调用点必须先有受信主体与逐案/操作授权，再在**同一调用方拥有的事务**首读前保留现有begin/报告完整内容/audit限制，读取报告RA和审计、逐份原件、构造引用并原子写入；成功提交后才返回。不能调用已经独立提交的 `_query_registered_pair` 后另开报告事务冒充同一视图。是否可将 `_read_registered_pair` 和现有纯投影用于该事务须在固定组合上验证；不得绕过Access责任或修改失败审计政策。

同时必须审查新类型存储注册、迁移、归档/恢复拒绝或兼容策略，保留只追加与跨案外键。本文不启用这些能力。重开后撤权不仅涉及链接：报告正文/冻结快照及新PDF/DOCX都不得泄露来源派生内容；已下载的导出不可撤回，另立验收。

## 依赖收敛与下一关

已证：T的真实纯合成临时SQLite登记→精确点→重建Database旧pin重读（afc72a1）；是组件级、测试Ctx，不是认证或报告保存。R的存储仅针对音频已做独立验收，不能迁移声称适用于轨迹。

未具备：可信报告授权装配、服务器持久选择关联、共同事务产品调用点、新类型存储与归档兼容、正文/导出撤权处理。因此本轮只交文档，不新增无可信上下文仍可保存的seam，也不制作玩具DB或假授权负例。

最短顺序：批准内部轨迹类型及可信report操作映射 → 固定同一源码组合并审计同事务调用点 → 合成负例（错案、无grant、错SHA/point、gap当点、无行、重复/缺句、旧引用重开与新原件共存）及真实SQLite原子性 → 归档/恢复与正文/导出授权单列 → 最后才考虑服务/UI。没有前两项不进入持久化实施。

本轮仅Git固定源读取、行号/函数对照、文档差异检查；未导入模块或运行DB/服务/浏览器/模型。没有报告归档闭环结论。

## 固定源码链接（逐一 Git 对象存在性检查）

- T [common/context.py](https://github.com/mark2wen2023/MCIS/blob/afc72a1180ae345556a85fb63a4020a476893d14/service/mcis_service/common/context.py)
- T [evidence_intake/router.py](https://github.com/mark2wen2023/MCIS/blob/afc72a1180ae345556a85fb63a4020a476893d14/service/mcis_service/evidence_intake/router.py)
- T [trajectory_exchange/registered_pair.py](https://github.com/mark2wen2023/MCIS/blob/afc72a1180ae345556a85fb63a4020a476893d14/service/mcis_service/trajectory_exchange/registered_pair.py)
- T [trajectory_exchange/registered_query.py](https://github.com/mark2wen2023/MCIS/blob/afc72a1180ae345556a85fb63a4020a476893d14/service/mcis_service/trajectory_exchange/registered_query.py)
- R [reports/access.py](https://github.com/mark2wen2023/MCIS/blob/94014643c02a1dd046ee8b0bfb76ae3b36631509/service/mcis_service/reports/access.py)
- R [reports/router.py](https://github.com/mark2wen2023/MCIS/blob/94014643c02a1dd046ee8b0bfb76ae3b36631509/service/mcis_service/reports/router.py)
- R [reports/generation_snapshot.py](https://github.com/mark2wen2023/MCIS/blob/94014643c02a1dd046ee8b0bfb76ae3b36631509/service/mcis_service/reports/generation_snapshot.py)
- R [reports/sentence_binding.py](https://github.com/mark2wen2023/MCIS/blob/94014643c02a1dd046ee8b0bfb76ae3b36631509/service/mcis_service/reports/sentence_binding.py)
- R [reports/sentence_binding_store.py](https://github.com/mark2wen2023/MCIS/blob/94014643c02a1dd046ee8b0bfb76ae3b36631509/service/mcis_service/reports/sentence_binding_store.py)

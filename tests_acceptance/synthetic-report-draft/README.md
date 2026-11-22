# 合成报告 → 来源可核候选草稿（本地评审）

基线 d5f78c405676a8b281c7f7d3247bdaf431503ae0；无生产调用方。
复用 research/semantic_support/evaluate.py 的 exact/text/ident/integer/array
标准库形状校验，不调用其公开报告语料或评估入口。
既有 agents/extraction.py 的逐字引文原则适用，但它是笔录问答与业务上下文，
本切片不导入、不假装它支持报告页段；也不转换到 ECFC V1。

运行：`python3 -I -B tests_acceptance/synthetic-report-draft/check.py`
九项 unittest，stdout 为两份合成结果，退出0才通过。
两份文本、模拟抽取及独立宿主标注都在 check.py 中手写；非模型/人工专家实测。
提取结果只能供应页、段、Unicode字符起点/长度与逐字引文；源摘要锁整个输入。
固定宿主标注提供 Event/Condition、命令或报告陈述、字面时间窗及冲突组。
它是透明的合成期望，不是可信生产关联，也不是任意报告的语义校验器。
源页段是手写文本的逻辑定位，不证明PDF页码或OCR位置。
宿主引文须为非空字符串，字符长度与 length 相等且末端不越段；尾段不得借切片截断放行。

第一输入含时间窗内的停车命令（执行未记载）和未知能见度；
第二输入有雾/无雾冲突、缺日期/时区、未知命令时刻；不调和冲突，不借段落补时刻。
输出逐字保留限定词，均为 Draft/ToBeVerified/isPresumptive；timeSeconds 始终null。
时间窗只是引文中的字面时钟，非UTC、精确事件时刻或可回放时间。
合成宿主明示的冲突组，采纳任一成员就必须保留完整组，否则报 incomplete conflict group。
两条相反记录均遗漏时允许其余候选，但 unselectedConflictGroups 明列未覆盖组。
extractionCoverageGuaranteed 始终为 false；即使明示组全部选入，也不保证提取覆盖或无其他冲突。
该限制只核宿主已标注组，不自动发现文本中的冲突。
无正式边、坐标、轨迹、场景可运行性、保存或报告导出。
普通负例覆盖凭空引文、页段/字符错位、加坐标/轨迹/因果字段、换源与重复。

下一门：正式报告来源读取/授权、页段稳定定位、审核解释/冲突与时间基准决策，
以及经评审的ECFC/场景适配；本地验证不替代任何这些能力。
本轮无服务、模型、浏览器、网络或数据库调用；未改契约与生产代码。


## 2026-11-11 20:22 · Damage/OrientedBoundingBox.Clearance 分离时净距偏小（W14 发现，DeepSeek 报）
两船分离时取各分离轴间隙的最小值，会低估真实净距，险情判定因此偏保守；碰撞判定不受影响。要求：分离时返回两 OBB 的真实最小距离（凸多边形最小距离，可用 GJK 或边-顶点穷举）。归属：W14 验收后排修（暂定 DeepSeek），需加回归用例，并重算 S1/S3/Y5。

### 处理方案（2026-11-11，只写方案、未改代码）

#### 1. 根因

现行实现见 `unity/Assets/_Project/Scripts/Simulation/Damage/OrientedBoundingBox.cs`（与 `p2p5-src/Simulation/Damage/OrientedBoundingBox.cs` 逐字节相同）。`Clearance`（第 56–106 行）用二维分离轴定理（SAT）检查两 OBB 的四条轴向（各船的首尾向、正横向）：

- 第 81 行：`gap = |中心差在轴上的投影| − (ra + rb)`，即该轴上的一维间隙。
- 第 82–88 行：若 `gap > 0`，记 `separated = true`，并取所有正间隙的最小值 `minSeparation`。
- 第 100–102 行：一旦判定分离，直接 `return minSeparation`。

这个返回值是「沿某一 SAT 轴把两盒平移到刚好接触所需的最小位移」，不是两凸矩形之间的欧氏最短距离。当最近特征是角对角（公共法向不落在任何一条 SAT 轴上）时，轴间隙最小值严格小于真实净距。面平行或点对边且公垂线正好沿某条边的法向时，两者相等，所以平行对驶、垂直 T 形等用例看不出问题。

注释第 53–54 行已写「分离时计算轴对齐的最小平移距离」，与上述行为一致，但与方法摘要「最小净距」不符。

**数值反例（轴对齐正方形，角对角）：**

- 盒 A：中心 `(0, 0)` m，航向 `0°`，半长 `1` m，半宽 `1` m，即平面正方形 `[-1, 1] × [-1, 1]`。
- 盒 B：中心 `(4, 5)` m，航向 `0°`，半长 `1` m，半宽 `1` m，即 `[3, 5] × [4, 6]`。
- SAT 东向间隙：`|4 − 0| − (1 + 1) = 2` m；北向间隙：`|5 − 0| − (1 + 1) = 3` m。现行 `Clearance` 返回 `min(2, 3) = 2` m。
- 真实最近距离是角点 `(1, 1)` 到角点 `(3, 4)`：`√(2² + 3²) = √13 ≈ 3.605551275` m。
- 已在 `/tmp` 用与生产代码相同的 SAT 公式、点到边穷举、以及每边 800 点的暴力采样交叉验证：SAT = 2 m，穷举与暴力采样均为 `3.605551275` m（差为 0）。该脚本未纳入仓库。

对照：同一套公式下，平行对驶（现有单元测试：中心北距 200 m、半长各 50 m）SAT = 真实 = 100 m；垂直 T 形面相对 SAT = 真实 = 20 m；刚好接触返回 0；交叉重叠返回负的 SAT 穿透深度（例：−75 m）。低估只出现在分离且最近特征不正对 SAT 轴的情形。

该问题已在验收中量化：`tests_acceptance/W14/CollisionGeometryAcceptanceTests.cs` 的 `SatClearance_CanUnderestimateTrueSeparation`、`tests_acceptance/W14/KnownIssueImpactTests.cs`、`logs/w14-clearance-sat-vs-true.csv`，以及 `DEFECTS/W14.md` 的 W14-D02。

#### 2. 修复算法

不引入 GJK。两矩形在二维只有 4 条边、4 个顶点，用点对边（自然包含边对边、角对角）穷举即可得到精确最小距离。验收夹具 `W14AccFixture.TrueObbDistance`（`tests_acceptance/W14/W14AccFixture.cs` 第 199–218 行）已经实现了分离分支，生产代码应把该算法上收到 `Clearance`，而不是在 What-if 层打补丁。

建议的 `Clearance` 流程（签名不变）：

1. **仍先跑现有 SAT 循环**，用于判定分离/重叠，并在重叠时计算现有的最小平移穿透 `minPenetration`。
2. **重叠或刚好接触**（`separated == false`）：保持现有约定，返回 `0` 或 `-minPenetration`（第 105 行，负值表示沿 SAT 轴的穿透深度）。不要改成 0，也不要改成另一种穿透定义。`CollisionDetector` 与现有重叠用例依赖这个符号和这个深度。
3. **分离**（至少一条轴 `gap > 0`）：不再返回 `minSeparation`。改为：
   - 取两盒 `GetCorners()` 各 4 个顶点；
   - 对 A 的每个顶点到 B 的每条边、B 的每个顶点到 A 的每条边，计算点到线段距离（点在线段上的正交投影夹到 `[0, 1]`）；
   - 返回这 32 次查询的最小值。
   二维不相交凸多边形的最短距离一定出现在「顶点–边」或「顶点–顶点」（后者是点到线段的端点情形），无需再单独做边对边平行检测。

**接口：** 不改 `public static double Clearance(OrientedBoundingBox a, OrientedBoundingBox b)` 的签名、命名空间和调用方式。只改分离分支的语义：正值由「SAT 轴间隙最小值」变为「欧氏最小距离」；0 与负值含义不变。更新第 52–55 行注释，写明这一约定。调用方代码不必改。验收夹具里的 `TrueObbDistance` 在修复后对分离情形应与 `Clearance` 一致，可保留作对照，或改为直接委托给 `Clearance`（实施时再定，不影响接口）。

#### 3. 影响面

**碰撞判定应保持不变。** 理由：SAT 的分离定理保证「存在正间隙 ⟺ 两凸盒不相交」。本修复只替换正值的大小，不改变 `Clearance` 的符号：分离仍 > 0，接触仍为 0，重叠仍 < 0。`CollisionDetector.FindFirstContactTime` / `BinarySearchContact`（`unity/Assets/_Project/Scripts/Simulation/Damage/CollisionDetector.cs` 第 40–41、50–51、80–81 行，以及 `p2p5-src` 副本）只判断 `clearance <= 0` 来定位首次接触时刻 `tc`，因此 `tc`、是否碰撞、`CollisionGeometry`（只用 `ApproximateContact`，不读净距大小）以及 `DamageModel.Assess` 都不应变化。对驶解析解用例（中心距 800 − 20t、半长和 100，`tc = 35 s`）应仍落在现有精度窗口内。

**会变的是未碰撞时的净距数值，以及依赖该数值与安全线比较的险情结论。**

| 调用方 | 用法 | 预期变化 |
|---|---|---|
| `ScenarioEvaluator.ComputeMinClearance`（第 200–203 行） | 未碰撞时在中心距最近点取 `Clearance`，再与 `SafeDistanceM`（默认 0.1 nm = 185.2 m）比较，得到险情 / 无碰撞 | 净距变大；部分情景可能改判 |
| `SensitivitySweep` | 用 `MinClearanceM` 求「达到安全净距」的临界提前量 | 碰撞临界值不变；安全临界值可能略减小 |
| `Yangze22Case` 偏差说明里的报告时刻净距 | 调用 `Clearance` 写报告 | 数值增大，结论文案需重算 |
| `CollisionDetector` / `DamageModel` | 只关心符号或接触点 | 不变 |

按 `logs/w14-clearance-sat-vs-true.csv` 与 `DEFECTS/W14.md` W14-D02（真实净距为 MinDistanceTime ±2 s 窗口内的最小值；修复后 `MinClearanceM` 仍取自中心距最近点的单点净距，与窗口最小值可能有很小差别，但不影响下表结论类别）：

| 情景 | 现行 SAT 净距 | 真实净距 | 现行结论 | 修复后结论 |
|---|---:|---:|---|---|
| 虚构 S1 | 127.6 m | 130.4 m | 险情（120–135 m 断言） | 仍为险情（130.4 < 185.2；数值仍大致落在原窗口） |
| 虚构 S3 | 52.4 m | 58.8 m | 险情（45–60 m 断言） | 仍为险情（58.8 < 185.2；数值仍大致落在原窗口） |
| YANGZE Y5 | 127.6 m | **362.9 m** | 险情（115–140 m 断言） | **改为无碰撞**（362.9 ≥ 185.2）。这是 W14-D02，也是本修复的主要产品影响。 |
| YANGZE Y1 | 199.1 m | 219.0 m | 无碰撞（180–220 m 断言） | 仍为无碰撞；219.0 紧贴现有上限 220 m，断言区间需要放宽 |
| YANGZE Y1+Y5 | 412.6 m | 420.7 m | 无碰撞（390–440 m） | 仍为无碰撞，区间可保留 |
| YANGZE Y4 | 23.1 m | 46.1 m | 险情（15–35 m 断言） | 仍为险情（46.1 < 185.2）；**15–35 m 的数值断言会失败**，需改为约 40–50 m |
| 虚构 S0 / S2、YANGZE S0 | 碰撞 | 0 | 碰撞 | 不变 |

因此：任务里「S1、S3、Y5 可能会变成无碰撞」——按已有量化，**只有 Y5 会改判**；S1、S3 净距会略增但仍低于安全线。Y4 结论不变但验收数值窗口必须改。

必须改写的测试：

- `DemoBoundaryAcceptanceTests`：S1 / S3 的 `InRange` 按重算结果微调（预计仍可通过，建议按真实净距核对后写入）。
- `Yangze22AcceptanceTests`：Y5 改为 `Avoided` / 「无碰撞」，放宽 `MinClearanceM`；Y1、Y4 的数值窗口按上表调整。
- `KnownIssueImpactTests.Y5_TrueClearanceCrossesSafeLine_VerdictShouldBeAvoided`（W14-D02）：修复后应变为通过，去掉 `KnownDefect` 特质（或按验收流程销项）。其中「SAT 净距 115–140 m」的断言要改成真实净距。
- `CollisionGeometryAcceptanceTests.SatClearance_CanUnderestimateTrueSeparation`：当前**断言** SAT 低估超过 5 m，修复后会失败。应改为断言 `Clearance` 与 `TrueObbDistance`（或暴力采样）在分离时一致。
- `CollisionDamageTests.ObbClearance_SeparatedAlignedShips_*` 与重叠、首次接触用例：平行对驶与符号判定不应受影响，应保持通过。
- `SensitivityComparisonAcceptanceTests`：碰撞临界值窗口 34.6–38.6 s 不应变；安全临界值窗口 171.4–175.4 s 可能略降，修复后重测再决定是否改期望。
- 开发侧 `ScenarioEvaluatorTests` / `Yangze22CaseTests`：一般只比较符号、单调性或确定性，预计无需改逻辑。

不要改 `tools/mcis-core/**`、W2、以及本方案阶段的 W14 / Damage 代码（实施阶段只应改 `OrientedBoundingBox.Clearance` 及其测试与文档中的期望值）。两份 `OrientedBoundingBox.cs` 必须同步修改。

残留限制（不在本次修复范围，但应在方案中明示）：`ScenarioEvaluator.ComputeMinClearance` 取的是「中心距最近点时刻」的单点 OBB 净距，不是整段航迹上 OBB 净距的全局最小。本修复不改变这一采样策略。`ApproximateContact` 仍是两中心中点（W14-D01），与净距算法无关。

#### 4. 测试计划

在 `CollisionDamageTests`（或新建 OBB 净距测试类）中增加回归，全部与暴力采样（每边密采样后的点对最小距离，容差约 1e-6 相对/绝对）对照。重叠用例不以暴力点对距离为准（点对距离为 0），而以现有 SAT 穿透约定为准。

| 用例 | 几何要点 | 期望 |
|---|---|---|
| 平行面相对（现有） | 同航向、中心距 200 m、半长各 50 m | `Clearance = 100`，与暴力采样一致 |
| 垂直 T 形、面相对 | 航向差 90°，沿正横分开 | 等于沿该向的面间距，与暴力采样一致 |
| 远距斜向同航向 | 类似验收里「斜向错开不相遇」的两船 | `Clearance` = 真实距离 ≫ 旧 SAT 值；与暴力采样一致 |
| 角对角 | 上文反例：中心 (0,0) 与 (4,5)，半长半宽均为 1 | `Clearance = √13 ≈ 3.605551275`，旧实现为 2 |
| 点对边 | 投影落在对边内部、公垂线沿某 SAT 轴 | 与 SAT 间隙相同，与暴力采样一致 |
| 刚好接触（面贴面、角贴边） | 中心距恰为半长之和等 | 返回 0 |
| 重叠 | 现有交叉重叠用例 | 仍为负值，数值与修复前 SAT 穿透深度相同 |
| 符号不变量 | 随机航向、尺寸、中心（分离/接触/重叠各一组） | `Clearance > 0` 当且仅当 SAT 判定分离；`<= 0` 与旧实现一致 |
| 对驶首次接触 | 现有 `BinarySearch_FirstContact_*` | `tc` 窗口不变 |

修复后重跑：`unity/DotnetTests2` 碰撞损伤测试、`unity/Tests_W14_WhatIf`、`tests_acceptance/W14`。更新 `logs/w14-clearance-sat-vs-true.csv` 所对应的量化用例，确认 Y5 为无碰撞，S1/S3/Y4 类别不变。按 REQUESTS 原条目要求重算并改写 S1/S3/Y5（及 Y1/Y4 数值）的对比表与结论文案。

#### 5. 风险与实施步骤

**风险**

- Y5 结论文案从「险情」改为「无碰撞」，属于对外结论变化，修复说明里必须写清是净距定义纠正，不是机动模型变了。
- Y1 真实净距约 219 m，现有验收上限 220 m，几乎顶格；Y4 数值窗口必改。若实施时采样时刻与验收窗口不完全重合，Y1 也可能略超 220 m。
- 安全临界提前量可能略降，碰到死窗口断言。
- 两份 `OrientedBoundingBox.cs` 若只改一处会再次分叉。
- 接触附近的浮点：应用与 SAT 相同的间隙阈值来分类分离/重叠，避免「SAT 认为刚分离、点到边算出极小负值」之类的不一致。分离分支只在 SAT 已判定 `separated` 时计算正距离。
- 不要把 `TrueObbDistance`「重叠返回 0」误写入生产 `Clearance`（生产重叠必须继续返回负值）。

**实施步骤（W14 验收结束后再动代码，本方案阶段不实施）**

1. 只改 `OrientedBoundingBox.Clearance` 的分离分支（unity 与 p2p5-src 同步），重叠分支与公开接口不动。
2. 先加第 4 节的单元回归（含反例 √13 与暴力采样对照），确认平行/接触/重叠旧用例仍通过，再改验收期望。
3. 重跑 Damage 与 W14 全部测试；按第 3 节调整数值窗口和 Y5 结论；将 W14-D02 从 KnownDefect 转为回归通过。
4. 重算并更新 S1/S3/Y5（以及 Y1/Y4）的净距与结论文案；碰撞相关数字应与修复前一致，若有出入则停止并核对符号路径。
5. 不修改 `tools/mcis-core/**`、W2、Cpa/Damage 的其它文件，以及 What-if 的机动与评价流程（除非只改测试期望或注释）。


## 2026-11-11 20:40 · W6：openapi 未描述 colreg:evaluate 可选请求体（DeepSeek 报，未改契约）
现有 `POST /api/v1/cases/{caseId}/colreg:evaluate` 在 `contracts/openapi.yaml` 中没有请求体。服务现已接受可选字段：`ownVesselId`、`targetVesselId`、`visibilityNm`、`vesselsInSight`、`inNarrowChannel`、`vesselStatus`、`inSightSamples`、`evidenceIds`、`thresholds`；未给出的字段回退到该案件存档的 colreg `inputs`（海力5 用此传入 19:51:15 起 `NotUnderCommand`）。请在 openapi 中补上该请求体说明。`colreg.schema.json` 无需修改。
已处理（Gemini bot 20:44）：openapi 补了 evaluate 的可选请求体和 422；PATCH 复核的说明也一起补了。


## 2026-11-11 20:58 · W18.1 / D06 裁定的语义后果：严格“任意 24h + 截断段按窗口内长度”会把标准 6+4、连续 10h 作息判违规（Claude Code 执行器报，请架构师复裁）
- 现状：W18.1 已按裁定实现精确的任意 24h（所有状态切换点 b、b−24h、b−7d 为锚点，锚点间按一次函数求解），与 `tests_acceptance/W18/b1_bruteforce.py` 1 分钟暴力扫描 40 组随机排班 0 差异。
- 后果（合成数据，可复现）：每日 01–07 + 13–17 的 6h+4h（STCW A-VIII/1 §3 明文允许的拆分）在窗口起点落在 6h 段内部时最长段 < 6h → LongestRest，且总 10h、两段之和 < 10h → RestSplit；每日连续休息 10h（08–18）在窗口从 13:00 起时被切成 5h+5h → LongestRest。即：只要休息段 < 12h，日周期作息几乎都会被判违规。暴力脚本给出同样结论，说明这是语义本身而非实现问题。
- 冲突：`tests_acceptance/W18/RestHourAcceptanceTests.cs` 的 `Split_6hPlus4h_Compliant`、`Split_5h59mLongest_LongestRestViolation`（期望 5h59m，严格语义找到 4h01m 更差窗口）失败；W18 自测中以 6+4 为合规基线的 8 项已改为单窗口（记录恰 24h）或暴力对照，并新增 `D06_DomainConsequence_DailyContiguous10h_IsFlaggedUnderStrictAnyWindow` 记录该后果。
- 可选方案（需裁定，未实施）：
  A. 维持严格语义（现状），在报告中说明拆分约束按任意窗口判定；
  B. 拆分约束（RestSplit / LongestRest）里被窗口边缘截断的休息段按完整段长计（Rest24h 总量仍按窗口内长度）。B 下 6+4、连续 10h 合规，但 D06 反例（[24,30) 被 24h01m 截成 5h59m）不再违规，D06 需撤回；
  C. 拆分约束只在“休息段起止点”对齐的窗口上判定（即 W18 修复版行为），并在裁定中写明不是严格任意窗口。
- 接口不变；A/B/C 都只改 `RestHourChecker.CheckSplit` 内部与相应测试。

## 2026-11-11 20:58 · W15.2 / D05 诊断码命名：裁定原文 `ref_not_checked` 与验收“全部 sys_ 前缀”冲突（Claude Code 执行器报）
- 现状：按裁定原文实现 `SystemicErrors.RefNotChecked = "ref_not_checked"`（Info 级，每种 kind 一条，ElementId = kind），另加 `SystemicValidation.NotCheckedRefCount` / `NotCheckedByKind` / `Infos`，`SystemicIssueSeverity.Info` 不影响 `IsValid`、不计入 `Warnings`。
- 冲突：`tests_acceptance/W15/RefsJsonAcceptanceTests.cs` 的 `ErrorCodes_AllSysPrefixed_AndUnique`（要求所有码以 `sys_` 开头）失败；`EachKindCheckedOnlyWhenProvided`（期望未传来源的种类完全不出问题项）与 D05“必须留痕”本身冲突。
- 提案：若架构师同意与 `sys_*` 风格统一，把常量值改为 `sys_ref_not_checked`（一处常量 + 测试，调用方用常量不受影响）；`EachKindCheckedOnlyWhenProvided` 建议改为过滤 Info 后断言。

## 2026-11-11 21:07 · W5 询问笔录比对：W3 比对结果缺陈述版本、台账无重新提交（Claude Code 执行器提，W3 合同变更提案，未实施）
- 问题 1：`CrossCheckResult` / `CrossCheckEntry` 不带陈述版本。陈述经 `ModifyStatement` 改了主张或时间后，台账里旧的比对结论仍会被 W5 视图当成当前结论展示，W5 无法识别“过期结论”。
  提案：`CrossCheckResult` 增加 `StatementRevision`（int，取自 `Statement` 的修改次数或审计序号）；`CrossCheckEntry` 增加只读 `IsStale(InterviewRecord)`；W5 视图对过期行显示“需重新比对”。
- 问题 2：`CrossCheckRegister.Submit` 对同一陈述已有条目时拒绝，没有“作废后重新提交”路径，比对失误只能 Dismiss，不能替换。
  提案：增加 `Resubmit(result, actor, utc, reason)`，旧条目进入 `Superseded` 状态并写审计；仅允许对 Pending / Dismissed 条目操作，Confirmed 条目需先撤销（如需再定义）。
- 口径说明（不需改合同，记录备查）：原型页名单把草稿矛盾也计为“N 处矛盾”，合同只认 Confirmed。W5 名单按合同只计已确认（未确认的以“M 条待确认”展示）；表头“7 条陈述 · 3 条矛盾”按原型计未驳回的（待确认 + 已确认）。

## 2026-11-11 21:19 · W3.2 批量审计 batchId 的落盘位置：建议 audit-event 合同增加扩展键 batchId（Claude Code 执行器提，未实施）
- 现状：按裁定实现两阶段提交，但 `contracts/schemas/audit-event.schema.json` 为 `additionalProperties: false`、`InvestigationAuditEntry` 只有 7 个标准键。为不改合同，batchId 以 “[batch=<32 位十六进制>]” 标记写在 `command` 字段末尾，`CrossCheckRegister.BatchIdOf` 解析、`CrossCheckRegister.EffectiveAudit` 重放过滤（无 commit / 计数不符 / 行在 commit 之后 / 旧行无 batchId → 作废）。
- 提案：audit-event 增加可选扩展键 `batchId`（落盘 snake_case `batch_id`），`InvestigationAuditEntry` 增加可选 `BatchId`；Data 层 `AuditLog` 重放时按同一规则过滤。合同改后再把标记迁移为键（解析函数保留以读旧行）。
- 相关验收用例需按裁定更新（只读未改）：`RetestAcceptanceTests.Batch_AllConsistent_ConfirmsAll_OneAuditEach`（n+3 → n+4，末行为 batch_commit）、`Batch_DuplicateIds_ConfirmedOnce_AuditedOnce`（n+2 → n+3）、`W31RetestAcceptanceTests.D07_Success_StateChangesOnlyAfterAllAuditsWritten`（写审计次数 5 → 6，各次已决定数仍全为 0）、`ToJson_CamelCaseKeys_IncludesConfirmedInBatch_MatchesSchemaPropertySet`（decidedUtc 期望值改为 `2026-05-19T04:00:00.000Z`）。
- 另：`Submit` 写审计失败仍抛异常（裁定只点名 Confirm/Dismiss，未改）；如要统一请裁定。

## 2026-11-11 21:19 · W5 询问笔录比对：W3 比对结果缺陈述版本、台账无重新提交（Claude Code 执行器提，W3 合同变更提案，未实施）
- 问题 1：`CrossCheckResult` / `CrossCheckEntry` 不带陈述版本。陈述经 `ModifyStatement` 改了主张或时间后，台账里旧的比对结论仍会被 W5 视图当成当前结论展示，W5 无法识别“过期结论”。
  提案：`CrossCheckResult` 增加 `StatementRevision`（int，取自 `Statement` 的修改次数或审计序号）；`CrossCheckEntry` 增加只读 `IsStale(InterviewRecord)`；W5 视图对过期行显示“需重新比对”。
- 问题 2：`CrossCheckRegister.Submit` 对同一陈述已有条目时拒绝，没有“作废后重新提交”路径，比对失误只能 Dismiss，不能替换。
  提案：增加 `Resubmit(result, actor, utc, reason)`，旧条目进入 `Superseded` 状态并写审计；仅允许对 Pending / Dismissed 条目操作，Confirmed 条目需先撤销（如需再定义）。
- 口径说明（不需改合同，记录备查）：原型页名单把草稿矛盾也计为“N 处矛盾”，合同只认 Confirmed。W5 名单按合同只计已确认（未确认的以“M 条待确认”展示）；表头“7 条陈述 · 3 条矛盾”按原型计未驳回的（待确认 + 已确认）。

## 已处理（Gemini bot 21:25）
- W18.1 拆分规则：采用方案 C 的规范化版本，详见 DEFECTS/W18.md 21:25。
- W5 的两条提案都接受：比对结果带陈述版本（statementVersion），台账增加 Resubmit（只能从 Rejected 发起，并写审计）。Claude Code 落实时同步更新 contracts。
- W3.2：Claude Code 的另一个执行实例在 21:10–21:19 完成，内容符合 DEFECTS/W3.md 的裁定，保留，送测。ROADMAP 中重复的 W5 行（21:07 / 21:19）以 21:19 为准。


## 2026-11-11 · W16 国际格式报告与 GISIS（Codex（W16 实现）提出，合同先行）
- 新 schema：`contracts/schemas/report.schema.json`；定义 report / section / sentence / citation / review / reviewRecord / gisisField / gisis / problem。生成内容为结构化数据的中英模板句，每句带来源引用，缺数据显式保留，证据引用经共享校验器标注 registered / unregistered。
- 新接口（均 `/api/v1`）：`GET /report-templates?caseId=`、`GET /report-glossary`；`GET/POST /cases/{caseId}/reports`；`GET /cases/{caseId}/reports/{reportId}`；`POST /cases/{caseId}/reports/{reportId}:generate`（201 新 reportId，同 familyId，version+1）；`PATCH /cases/{caseId}/reports/{reportId}/sections/{sectionId}`（可选 sentenceId，返回章节）；`GET .../reports/{reportId}/audit`；`GET .../reports/{reportId}/export?format=pdf|docx&lang=zh|en|bilingual`；`POST /cases/{caseId}/reports/sections/colreg:draft`（返回 section、reportId、reportHref、report，外部接入 W6 按此路径）；`GET /cases/{caseId}/gisis`、`POST /cases/{caseId}/gisis:validate`、`GET /cases/{caseId}/gisis/export?format=json|csv`。
- 创建体 `{templateId: imo-cic|maib|cn-msa, lang: zh|en|bilingual}`。复核体 `{action: confirm|dismiss|modify, reason?, textZh?, textEn?, sentenceId?}`；confirm/dismiss 禁任何新值字段（包括 null），modify 须有新文本且有实际变化；新生成全 Draft，确认不改 source，修改 source=Investigator，原 generatedText 保留；人工复核旧版本永不被重新生成覆盖。
- 审计：使用现有 audit.append 写 audit-event（reason 已支持落盘行扩展），报告包另存完整 beforeValue / afterValue / reason 与 auditSeq。报告审计查询返回 `{auditEvent, reportId, sectionId, sentenceId, reason, beforeValue, afterValue, summary}`，避免改变 audit-event 严格合同；summary 可截断，reason 原文不截断。
- GISIS 为本地准备字段，**不表示已提交或已正式接通 IMO GISIS**。字段含中英标签、必填性、sourceRefs（案件字段路径/证据编号）、rules、value（缺值 null）、missing、missingLabel。多船字段按 `vessels.<vesselId>.<字段>` 展平，绝不用排水量替代总吨；事故等级做显式枚举映射，不从自然语言补造伤亡、污染、灭失或调查国。
- 校验体 `{values?: {字段id: 值}, export?: boolean, format?: json|csv}`；覆盖值仅本次校验/导出，不写案件。普通校验返回 `{valid, errors, fields}`（有错仍200）；export=true 且校验通过返回文件流，否则422。GET JSON/CSV 允许缺数据，但必须保留 null/missing。文件响应 Content-Disposition + X-Sha256，每次生成、复核、导出与 GISIS 校验导出均写审计。
- 错误码：409 `report_real_data_pending`（真实数据使用待 Mark 本人确认）；404 `report_not_found` / `report_section_not_found` / `report_sentence_not_found`；422 `report_invalid_argument` / `report_review_reason_required` / `report_review_no_change` / `report_review_field_not_allowed` / `report_review_text_required` / `report_gisis_validation_failed`；沿用权限 FORBIDDEN / READ_ONLY 与 CASE_NOT_FOUND / CONTRACT_VIOLATION。
- 真实/虚构：仅 isFictionalDemo=true 开放生成/导出；海力5 `CASE-2025-HAILI5-WANA17`、YANGZE 22 `CJK-2024-1230-YangZe22-VegaDream`（规范 caseId，按 DEFECTS/W12.md 21:52 裁定，原占位 CASE-REAL-YANGZE22 已废弃） 返回 realDataStatus=pending-confirmation，任何生成/导出409且不写库；不读真实报告目录、不调用 colreg evaluate。未知非虚构案件同样关闭。
- 标准依据：IMO MSC.255(84) 第14章规定调查报告提交/公开，**具体报告要素清单在2.12**，IMO模板同时映射两处；MAIB 六部分结构；中国海事模板用“原因分析与教训”，本系统不作责任认定。SMCP中文为项目译文。参考：https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MSCResolutions/MSC.255(84).pdf 、https://www.imo.org/en/ourwork/iiis/pages/reporting.aspx 。
- 需 Gemini 裁定：① 本地 GISIS 字段到正式 MSC-MEPC.3/Circ.4/Rev.1/平台字段映射及必填条件；② W14/W15 服务尚未提供，保留可插拔 missing 适配器，未来来源接口/合同；③ 中文海事模板以安全调查教训替代责任节的正式名称；④ W6 外部接线到独立 ColregDraftButton（不改并发文件）；⑤ 报告审计完整快照独立存储、audit-event维持现合同，是否后续统一扩展。


## 2026-11-11 21:31 · W6.1 避碰规则对照页修复：合同待补项（实施 A 提，未改 schema / openapi）
按 DEFECTS/W6.md 文末 12 条裁定实现后，以下内容 schema/openapi 尚未描述，现以“不进 schema 的扩展”落地，请 Gemini 裁定是否写入合同：
- **colreg schema 扩展字段**（colreg.schema 为 additionalProperties=false，故未写入 colreg 文档本体，存于版本注解 `run:R-000N.annotations`）：`bands[].evidenceIds`（时间带证据，裁定 3/4）；`checks[].reviewedBy / reviewedAt / engineVerdict / engineSource / lastAction / reason / history[]`（裁定 2/5）。建议 colreg.schema 增加这些可选字段。
- **audit-event 扩展键 `reason`**：`audit.service.build_line/append(reason=...)` 把完整理由写进 JSONL 落盘行（在哈希链内、不截断），DB 列与 `to_doc` 未改，audit-event 文档仍 schema 合法；`after` 摘要仍按 400 字截断。W6 验收 B2 断言 `after` 含全文，与此实现冲突，请裁定以 `line.reason` / 复核历史接口为准，或在 audit-event 增加可选 `reason`。（W16 已复用此扩展键。）
- **新增接口（已实现，`include_in_schema=False`，openapi 未声明）**：`GET /cases/{caseId}/colreg/runs`（版本列表）；`GET /cases/{caseId}/colreg/runs/{runId}`（runId 可为 `active`）；`POST /cases/{caseId}/colreg/runs/{runId}:activate`（设为当前版本，写审计 `colreg.activate`）；`GET /cases/{caseId}/colreg/compare?base=&other=`（两版本逐条对比）；`GET /cases/{caseId}/colreg/checks/{checkId}/reviews?runId=`（完整理由的复核历史）。`PATCH .../colreg/checks/{checkId}` 新增可选 `?runId=`。
- **evaluate 二次确认（裁定 9）**：非虚构案件不带 `?confirmToken=` 时返回 **409 `colreg_evaluate_confirm_required`**，detail `{caseId, isFictionalDemo:false, confirmToken, expiresInSec:300, nextVersion}`；令牌绑定案件+操作员、一次性、5 分钟有效；错误/复用/他人令牌 409 `colreg_evaluate_confirm_invalid`。每次 evaluate 产生新版本 `R-000N`（kind=RuleEngine）并设为当前，种子与复核记录保留在旧版本，不覆盖；写审计 `colreg.evaluate`（entity colregRun）。evaluate 响应仍为 colreg 文档本体，不带 runId（新 runId 通过 `GET runs` 的 activeRunId 取）。
- **evaluate 请求体 `vesselStatus`**（裁定 1）：只接受对象 `{vesselId: [{fromUtc, status}]}`（fromUtc 须为 UTC，Z/+00:00）；旧 list 形式 422。W6 验收 F7（记录 list 形式现状）因此失败，属按裁定改变。存档 inputs 里遗留的 list 仍兼容读取。
- **复核请求体**：主字段 `{action: confirm|dismiss|modify, verdict?, reason?, evidenceIds?}`；仍接受旧别名 `reviewStatus/note`（两者矛盾时 422）。confirm/dismiss 带 verdict → 422 `colreg_review_verdict_not_allowed`；dismiss/modify 缺理由 → 422 `colreg_review_reason_required`；modify 缺 verdict → `colreg_review_verdict_required`、无变化 → `colreg_review_no_change`；未登记证据 → 422 `evidence_not_registered`（detail `{field, unregistered, badFormat}`，evaluate 的 evidenceIds 同样校验）。
- **章节草稿按钮（裁定 11）**：前端调用 W16 openapi 已声明的 `POST /cases/{caseId}/reports/sections/colreg:draft`，体 `{lang:'zh'}`，兼容响应 `{section, reportHref}` 或裸 section；接口未实现（404/405/501）时显示友好提示。后端由 Codex 在 W16 实现，W6.1 未实现。

### W16 实现补充（Codex，2026-11-11）
- 报告完整快照可能引用 Restricted 证据与询问比对。W17 尚无报告字段脱敏适配，本包对报告实体、审计、导出及 GISIS 业务入口先限定 LeadInvestigator / Investigator（其余角色403 FORBIDDEN），再执行现有 report_draft 权限检查；不改共享矩阵，模板/术语接口可读取。请 Gemini 裁定后续字段脱敏出口。
- 章节单独生成的报告重新生成时保持原单章节范围；无效 sentenceId 类型/空值返回422；GISIS 临时覆盖来源标明 request.values 字段，原案件不变。校验导出失败 detail 返回完整 {valid,errors,fields} 便于页面展示。
- W16 合同收尾：新增 pending 与 auditRecord 定义，报告详情响应为 Report / ReportPending 二选一；审计响应显式引用 ReportAudit，真实待确认回包与完整快照均可按合同验证。

### W16 交付验证与并发集成记录（Codex，2026-11-11）
- W16 无 socket 测试加 schema 合法性共72项通过；W16 tag下13个OpenAPI操作逐项与服务一致；web test:w16为111断言通过，tsc通过。HTTP TestClient测试在本沙箱40秒无输出后超时（exit124），保留test_reports_w16.py由外部执行。
- 并发期间全局test_openapi_yaml_matches_routes出现5条W6.1差异：OpenAPI已新增runs/list/detail/activate、compare、check reviews，但colreg/router.py仍PENDING_CONTRACT=True（隐藏于app.openapi）。本包未改W6，需W6/Gemini集成时同步公开路由。
- 外部页面整合：独立ColregDraftButton已提供；Layout当前仅按colreg的case参数切换顶栏案件，报告页内部真实/虚构和待确认状态已正确显示，Layout不在本包改动授权内。


## 2026-11-11 21:50 · W12 分析页：合同待补项（实施 A 提，未改 schema / openapi）
- **新增只读接口（已实现，`include_in_schema=False`，`analysis/router.py` 的 `EXTENSION_ROUTES` 列出，test_analysis_w12 核对）**：
  `GET /api/v1/analysis/cases` → `{cases:[{caseId,key,title,isFictionalDemo,sourceLabel,hasWhatIf}], seedSha256, seedVerified, generatedAt, coreVersion, coreDll, w14Export, w14Frozen, crossCheck, disclaimer}`；
  `GET /api/v1/cases/{caseId}/analysis`（caseId 也接受 key：lily-mary / haili5 / yangze22）→ 案例 + `baseline{series[{t,clock,distanceNm,dcpaNm,tcpaMin,riskLevel}], keyMoments[]}` + `whatif{rows[], antennaSensitivity[], inputs[], assumptions[], safeDistanceM, criticalMarginM}`（海力5 为 null）+ `meta`。
  错误：404 `analysis_case_not_found`；500 `analysis_seed_tampered`（种子与 .sha256 旁注不一致）。请裁定是否写入 openapi（建议新建 analysis.schema.json）。
- **数据来源**：运行时只读预生成种子 `service/mcis_service/analysis/data/w12-analysis-seed.json`；曲线由已构建 mcis-core cpa 离线计算，W14 数值来自项目外临时目录只读运行的 W14.2 导出，与 Codex 复测留档逐项一致（52 值，偏差 0）。见 logs/w12-export-howto.md。
- **YANGZE 22 caseId 不统一**：本页用 `reports/yangze22/case.json` 的 `CJK-2024-1230-YangZe22-VegaDream`；W16 用占位 `CASE-REAL-YANGZE22`。请定一个。YANGZE 22 未入服务数据库（无 `/cases/{id}`），是否要播种入库也请裁定。
- **共享文件 Layout.tsx**：W6.1 验收（21:43 有条件通过）之后才改，补丁见 logs/w12-layout.patch：分析页也按 `?case=` 切换顶栏；`/cases/{id}` 404 时（YANGZE 22）回退到 `/analysis/cases` 取标题与虚构标志。只在 /analysis 路径生效，colreg 行为不变。

## 2026-11-11 21:59 · W16 外部验证与补充（Codex bot 主控，沙箱外）
- **W6 按钮已接通**：W6.1 的 ColregPage 已按本包路径调用 `POST /cases/{caseId}/reports/sections/colreg:draft`（体 `{lang:'zh'}`），响应 `{section, reportId, reportHref, report}` 与其 normalizeDraftResponse 兼容；临时端口浏览器实测点击“生成规则分析章节草稿”显示 Draft 章节和“打开报告草案”链接。故上文“需 Gemini 裁定 ④”已无需接线，`web/src/reports/ColregDraftButton.tsx` 作为独立备用组件保留（未挂到任何页面），是否删除请裁定。
- **章节范围**：colreg:draft 生成的章节 `dataSources` 只列 `colreg-check`、`evidence`（与实际句子一致；原先沿用模板分析节会多列 W14/W15/询问比对）。
- **web 请求改走同源 `/api`**（与 src/api.ts 一致，由 vite 代理到 MCIS_API 配置）；直连 SERVICE_URL 在临时端口 preview 下被 CORS 拦截。
- **GISIS 导出被拒也写审计**：`POST /gisis:validate {export:true}` 校验不通过时，除 `report.gisis.validate` 外另写 `report.gisis.export_rejected`（after 含 errors），再返回 422。
- **外部测试结果**：pytest 全量（项目副本，忽略读取 reports/ 真实数据的 test_analysis_w12.py）222/222 通过，其中 W16 113 项；W16 前快照基线 94 项全部包含且通过。web：test:w16 111 断言、colreg-render 18、colreg-w61 43 全过；tsc 0 错。

## 2026-11-11 22:04 · W16 口径更新（Codex bot，按 Gemini bot 两条口径）
- YANGZE 22 真实案例入口改用规范 caseId `CJK-2024-1230-YangZe22-VegaDream`（DEFECTS/W12.md 21:52 裁定），占位 `CASE-REAL-YANGZE22` 废弃；仍只留接口，GET 返回 pending-confirmation，生成/导出 409 `report_real_data_pending`，不读 reports/。schema/openapi 的 W16 部分原本无该占位示例，无需改动。
- W16 样式从共享 `web/src/styles.css` 整段迁到 `web/src/styles/w16.css`，由 `main.tsx` 紧接 `./styles.css` 之后引入（层叠顺序不变）；styles.css 只删除 W16 那段，其余内容逐行未变。

## 2026-11-11 22:20 · W16.1 合同变更（Codex，按 DEFECTS/W16.md 22:10 裁定；先登记后实现）
- **audit-event 增加可选 `snapshotRef`**（裁定 4）：`contracts/schemas/audit-event.schema.json` 新增可选字符串 `snapshotRef`，指向完整快照，格式 `report-snapshot:RA-<32位十六进制>`（以后其他包可用 `<种类>-snapshot:<id>`）。落盘 JSONL 用扩展键 `snapshot_ref`（与 `reason` 一样进入哈希链；C# AuditLog.ReadAll 忽略扩展键）；`audit.service.to_doc` 只在行内有该键时输出 `snapshotRef`，旧行和别的包的行**不受影响**（不传时落盘行逐字节不变）。`reason` 键照旧。
- **新接口** `GET /api/v1/cases/{caseId}/report-snapshots/{snapshotId}`：按 snapshotRef 取完整快照 `{snapshotId, reportId, sectionId, sentenceId, reason, beforeValue, afterValue, summary, auditSeq}`，权限与报告审计相同（仅 LeadInvestigator / Investigator）；真实案例 409 `report_real_data_pending`；不存在 404 `report_snapshot_not_found`。报告审计列表每项增加 `snapshotRef`。
- **GISIS 字段**（裁定 1）：对照表见 `contracts/gisis-mapping.md`。`report.schema.json` 的 gisisField 增加可选 `gisisRef`（通函条目，如“附录2 1.1*”）、`mappingStatus`（exact / partial / none / pending）、`mappingNote`；必填改按通函星号（总吨、伤亡、污染、灭失、报告状态改为非必填）；新增 `numberOfShips`（附录1·一般信息 .2*）、`locationCategory`（附录1·一般事故数据 .6*，Table 3）；`severity` 取值改为 Table 5 三档，本地 Serious / LessSerious 对应哪档待核，遇到时输出缺数据。
- **W14 来源**（裁定 2）：报告的 whatif 适配器改读 W12 分析种子（与 `GET /cases/{caseId}/analysis` 同一来源，进程内调用 `analysis.router.load_seed()`，带哈希自检）。只接受 `isFictionalDemo=true` 且 sourceRefs 不指向 `reports/` 的条目（即 Lily/Mary 虚构情景）；海力5 / YANGZE 22 条目依赖 reports/ 真实报告，在 Mark 本人确认前不读，报告侧本来也是 409。W15 继续显示缺数据。
- **删除** `web/src/reports/ColregDraftButton.tsx`（裁定 7）。

### W16.1 实现说明（Codex，2026-11-11）
- GISIS 按 `contracts/gisis-mapping.md` 逐字段提供 `gisisRef` / `mappingStatus` / `mappingNote`，按本地必填列校验；新增案件船舶数和显式 Table 3 水域类型，未填不推断。Table 5 仅映射已确认的两个本地等级，其余输出缺数据并保留待核说明；JSON / CSV 均保留映射信息。页面突出待核，规则 JSON 只放在默认收起的 `<details>`。
- 审计 `build_line` / `append` 新增可选 `snapshot_ref`，不传时固定输入字节回归保持不变；`to_doc` 仅在原行解析出该键时输出 `snapshotRef`。报告操作将 `report-snapshot:RA-…` 写入哈希链，报告审计每项带引用；旧快照也可取回，不改写旧审计行。
- 已实现 `GET /api/v1/cases/{caseId}/report-snapshots/{snapshotId}`，返回登记的完整快照（含 `snapshotId`、`auditSeq`、理由全文、前后值）；仅 LeadInvestigator / Investigator，沿用报告审计权限；真实案例 409 `report_real_data_pending`，不存在或非本案件的快照 404 `report_snapshot_not_found`，其它角色 403 `FORBIDDEN`。OpenAPI 增加路径与 `ReportSnapshot` 组件，报告 schema 增加快照定义和审计引用。
- W14 仅通过 `analysis.router.load_seed` 读取带哈希自检的 W12 种子，按 caseId 精确匹配并先检查虚构标志及 sourceRefs，真实或 `reports/` 来源只显示待 Mark 确认；种子异常降级为缺数据。逐行情景句包含原字段值和可解析的分析页情景引用，另列免责声明与假设数量；英文结构中的情景名、说明和免责声明保留种子原文。W15 继续缺数据。
- 独立 `#/report` 页头增加使用当前模板的双语生成按钮；安全建议页头增加携带当前 `CASE_ID` 的报告入口；删除未引用的 `ColregDraftButton.tsx`。中国海事模板只增加指定 TODO 与 `standardRefs[].pendingRuling` 页面标签，原章节保留；YANGZE 22 不入库，角色限制不变。
- 测试先红后绿：GISIS 新增 15 项初次失败、快照新增 13 项初次失败、W14 来源初次 8 败 / 4 过，web 新断言初次失败。实现及旧断言按裁定改写后，服务端无 socket 定向回归 108/108 通过（`test_reports_w16_direct.py`、`test_reports_w16_export.py`、`test_reports_w16_sources.py`、新增 `test_reports_w161_gisis.py` / `test_reports_w161_snapshot.py`）；web `npm run test:w16` 140 断言通过，`npx tsc --noEmit -p tsconfig.app.json` 通过。
- `timeout 30s .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_reports_w16.py` 在沙箱无输出超时，exit 124；该文件已补 HTTP 快照往返与权限/错误码用例，需外部环境补跑。未读取根 `reports/`、未导入 `analysis/build_seed.py`，未修改 ROADMAP、未生成冻结清单或哈希、未启动服务或截图。

## 2026-11-11 22:25 · W16 进度（Codex bot，收尾停点）
按 Mark 收尾要求停在此处，W16.1 不再继续。
- **状态**：W16（22:04 冻结版）已交付待验收，冻结清单 `logs/w16-impl-hashes-frozen.txt`（26 项）。之后按 DEFECTS/W16.md 22:10 裁定开工的 W16.1 已改动代码，**未标待测、未冻结**，所以 W16 冻结清单里的部分文件已经变了，验收时请以 W16.1 为准，或重新冻结。
- **W16.1 已完成**（见上一节实现说明）：裁定 1 GISIS 对照表 `contracts/gisis-mapping.md`、gisisRef/mappingStatus、校验 JSON 收进折叠区；裁定 2 W14 读 W12 分析种子（只取虚构条目），W15 仍为缺数据；裁定 4 audit-event 可选 `snapshotRef` + `GET /cases/{caseId}/report-snapshots/{snapshotId}`；裁定 7 删除 ColregDraftButton.tsx；裁定 8 `#/report` 页头加生成按钮，`#/recs` 加报告入口。
- **W16.1 已验证**：无 socket 的服务端定向测试 108/108（test_reports_w16_direct/_export/_sources、test_reports_w161_gisis/_snapshot），web `test:w16` 140 条断言，tsc 通过。
- **还差**：
  1. 在沙箱外补跑 `service/tests/test_reports_w16.py`（HTTP 用例，含快照往返）和 pytest 全量。
  2. 重拍 `screenshots/w16/` 1440/1920。
  3. 重算冻结哈希（上一版另存 v2），在 ROADMAP 标 W16.1 待测。
  4. 裁定 3：中国海事模板章节标题逐字采用 reports/ 原文。**未做**，只加了 TODO 和 pendingRuling 标签。原因是 Mark 本人还没确认真实报告可用。
  5. W14 的海力5/YANGZE 22 条目、YANGZE 22 入库（下一包）也都等 Mark 确认。
  6. GISIS 里 Table 5 本地等级对应和部分字段仍标「待核」。
- **W16.1 改过的文件**：contracts/schemas/audit-event.schema.json、contracts/schemas/report.schema.json、contracts/openapi.yaml、contracts/gisis-mapping.md（新）；service/mcis_service/audit/service.py、service/mcis_service/reports/{templates,gisis,sources,service,router}.py；service/tests/test_reports_w16.py、test_reports_w16_direct.py、test_reports_w16_export.py、test_reports_w16_sources.py、test_reports_w161_gisis.py（新）、test_reports_w161_snapshot.py（新）；web/src/reports/{ReportView.tsx,types.ts}、web/src/pages/{ReportPage.tsx,RecommendationsPage.tsx}、web/src/styles/w16.css、web/tests/report-render.test.tsx；删除 web/src/reports/ColregDraftButton.tsx；REQUESTS.md。改动前备份在 /workspace/w16-backup/。日志 logs/w16.1-codex-*。
- 未做任何 GitHub 操作，未 push。

## 2026-11-11 W16.1 继续开发：公开报告来源适配切片

用户在本次续作对话明确说明「里面没有敏感资料 都是公开发布的报告 都可以用」。该许可仅用于项目内部开发/测试，不扩展为对外发布许可。
本切片修改 reports/sources.py（既有 W16 冻结范围）及自测：允许海力5、YANGZE 22 的 W14 条目从已做 SHA256 校验的 W12 seed 进入报告来源适配，逐条保留 seed 定位、来源文件/哈希与【推算】标注。不重算、不修改 W12 seed；无 W14 结果仍显示缺数据。未解锁报告 HTTP 入口、未导入 YANGZE 22 数据库，未修改模板或共享合同。完整 W16.1 的上述后续工作仍待完成。

## 2026-11-11 W16.1 公开报告链路续作登记（实现前）
沿用本次用户公开报告使用许可，修改既有 reports/service/router/gisis/exporter、templates 及报告前端、report schema/OpenAPI 的冻结范围。新增 realDataStatus=`authorized-public`（仅明确允许的公开案例），未知真实案例仍 pending-confirmation。海力5已入库，开放原有调查员权限下生成/复核/审计/导出；YANGZE 22 尚未入库，不用占位案生成，列表额外 blockedReason=`report_case_not_imported`，相关操作409同名错误，导入仍为下一包。中国海事模板按两个原文逐字标题，IMO/MAIB不变，缺少映射的章节明确缺数据，不把推算冒充责任认定。不改变访问角色、不外网监听、不推送或部署。

## 2026-11-11 YANGZE 22 入库与原文摘录续作（实现前登记）
按本次继续开发及公开报告使用许可，修改已冻结 service/main.py、reports/service.py/router.py/sources.py、相关测试和前端案件文案，新增幂等公开种子与原文摘录模块。仅使用 reports/yangze22/case.json/report.txt 已有来源；不制造航迹、不将国内事故等级未经确认映射IMO等级、不把原报告责任认定当本系统的新认定。入库不覆盖已有用户案件；原文摘录保留来源/hash/页码，仍是Draft。原W16.1-public-flow冻结清单保留历史，本轮另行冻结。对正常入库YANGZE开放现有调查员链路；缺失案件仍保留not_imported检查，不改安全角色或对外发布范围。
正文续作附加：修改reports/exporter.py与ReportView引用表，保留同一证据不同sourceRef的条目并显示出处，避免17章引用折叠为一个不含页码的引用。新增PDF/DOCX来源定位回读测试，不改变引用schema。

## 2026-11-11 验收续作发现：YANGZE分析页过时入库提示
W12.1独立验收发现冻结seed的notes仍写“本案未接入服务数据库”。本轮YANGZE已入库，该文案已过时。登记修改已冻结analysis/router.py：仅响应副本改为“基线曲线来自W14 S0报告航迹重建；入库状态以案件管理为准”，不改seed字节/哈希/缓存，不重算任何数值，不增加数据库写入或权限范围。新增独立回归确认数值/来源完整保留；此改动独立于W12.1原冻结验收结论。

## 2026-11-11 验收工装可移植性与提交授权
- W6/W12验收launcher从原机硬编码路径改为仓库相对路径，支持MCIS_DOTNET；服务测试conftest也按MCIS_DOTNET识别真实SDK，防止SDK已存在却误跳过。没有改引擎结果或删除验收用例。
- W6旧PATCH/F1用例、W3可选statementVersion断言按既有架构裁定改写；新增严格回归见各独立验收记录。
- 本次对话用户明确允许完成后提交独立分支并创建PR，不允许直接合并main或部署。此前“未push”记录为阶段事实，最新远端操作以PR记录为准。

## 2026-11-11 真实浏览器发现的案件上下文缺陷
本轮实际报告页面验证发现：报告内容为YANGZE真实案，但共享Layout仍显示固定Lily虚构案；证据/建议引用链接也可能进入固定默认案。登记修改共享Layout.tsx（另记本轮哈希，不覆盖其他包历史清单）、新增caseContext.ts、api.casePath兼容可选caseId及EvidencePage/RecommendationsPage读取/写入上下文。仅对已支持按案工作的report/colreg/analysis/evidence/recs保留case查询，未支持页面仍用默认案；切案清旧状态/忽略过期响应，不允许旧案操作落入新案。角色和服务权限不变。源码/浏览器回归后另行冻结，不改既有已冻结历史清单。

## 2026-11-11 当前 CLI 可重现构建与候选分析基线（实现登记）
历史 DLL 已在隔离副本精确恢复，确认 W5.1 Evidence 输入与历史生成输入不同。经本次续作授权，新增内容寻址、固定 SDK 8.0.428/PathMap/无 Git 后缀的隔离 CLI 构建器，wrapper 从时间戳改为所有 Compile 输入哈希校验（包含 Evidence）。不修改 csproj、历史源码/seed/断言。先在项目外隔离副本运行原 build_seed 完整生成候选，并比较全部 14539 数值与历史固定指纹；经独立审查后才能纳入当前基线。历史来源与恢复脚本保留，不以替换哈希伪造重算。

## 2026-11-12 W12 历史 Layout 架构断言适配（独立验收）
已授权的案件上下文修复把路由选择移至 caseContext helper，原 W12 用例硬编码 `colreg || onAnalysis` 字符串不再对应实现。保留原测试名称和分析页专属 `/analysis/cases` 回退要求，改为验证当前 helper 接线，并实际执行 Layout 加载 effect：仅 analysis 在案件读取失败时访问分析清单，colreg/report/evidence/recs/其他页不得回退。此处仅改验收，不改实现、不删除用例、不放宽 fallback 独占性或数值断言。

### 当前 CLI 基线纳入与完整复验完成
独立审查确认当前 Linux / SDK 8.0.428 多临时路径构建一致，原 build_seed 真正重算，14539 数值逐项相同且仅时间/DLL SHA变化。将原 seed+旁注逐字节归档至 service/mcis_service/analysis/data/history/w12-original-20261111/（附恢复说明），安装已审查候选并由新 wrapper 重建 DLL；不改历史冻结清单/数值断言。完整服务首次315过1败为mcis-compat依赖DOTNET_ROOT未配置，保留日志；正确配置同一SDK重跑316/316通过。W12+provenance30/30、独立W12 21/21、报告前端148断言通过。详见 logs/current-core-seed-candidate.md 及 installed-provenance.json。未部署、未合并，提交由主控处理。

## W18.2 D08 实现登记（续作）
按 DEFECTS/W18.md 21:49 裁定，修改已冻结的 `Domain/HumanFactors/RestHours.cs`：拆分规则的乐观/悲观视图按相同候选窗口先分类，再分别归组，避免边界截断导致的数据不足窗口被相邻确定违规组吞掉。总量/间隔规则不改变。Assumptions补齐指定记录首/尾窗口说明；新增实施自测，保留既有D08及220组独立参考、真实案例回归。无公共API/schema变化，不修改W14/W12来源链；实现后另冻结并交独立验收。

## W14.3 D06 实现登记（续作）
按 DEFECTS/W14.md 21:12 裁定，修改已冻结的 `Simulation/WhatIf/ScenarioEvaluator.cs` 及 `WhatIfSetup.cs` 算法假设文本：净距扫描覆盖两船实际积分时刻和积分dt网格，在局部极小/高转首率区间加密，0.5°/s仅为数值加密阈值而非风险或航海规则。动力学、碰撞检测、安全距离与W12生成链保持不变。新增实施测试，原独立验收断言不由实施方修改。先记录D06红基线和当前YANGZE五情景，再检查窄谷对0.01s暴扫≤0.1m、五情景净距偏差≤0.01m及判定/碰撞/临界敏感性；超限先报告，不刷新seed/来源哈希。缺失上游文件逐Git blob核验并记持久manifest，不stage/push。

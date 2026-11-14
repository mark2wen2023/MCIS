
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

## W13.1 本地回放命令适配小切片（2026-11-12）
- 仅新增纯 C# Presentation/ReplaySync，复用 ISimClock；不改变 HTTP/JSON 合同，不声称 Unity 场景或网络接通。
- 命令 DTO 对应 sim-state.schema.json。按 case 验证后去重；序列必须连续，构造可显式传已确认游标。批次排序，重复序列 payload 冲突预检拒绝（无副作用）。历史确认游标前未持有 payload 的命令拒绝，不能验证其一致性。
- 成功 payload 仅本实例生命周期记忆；重启持久化、主线程调度由上层负责。缺口/非法命令停止，不推进游标；所有数值/必需参数先验证。seek 越界在调用前拒绝，同点沿用实际时钟事件语义；上层先配置案件区间。仅消费上层已授权并正确映射的命令，不替代认证或 HTTP。
- setRate 仅现有时钟支持的八档；focusVessel 仅注入意图，不表示相机成功移动。时钟/回调异常可能已经生效，返回 FailedUnknown 并锁住实例，不可自动安全重试，不承诺 exactly-once。
- 状态快照只读；不实现 HTTP、10Hz 网络发布或 Unity 画面。纯逻辑验收与 netstandard2.1/C#9 编译独立完成。

### W13.1 独立验收登记
新增独立 `tests_acceptance/W13`，冻结后只读引用适配器与现有真实ISimClock实现。验收按case隔离、连续序列/重复/乱序/冲突、非法参数拒绝无副作用、越界seek与不支持倍速预检拒绝、异常可能已生效时锁实例不自动重试、仅显式checkpoint边界的重启语义、focus意图回调及只读状态快照。真实Clock验证seek误差<0.1s与play/pause/rate推进，不改Clock或server合同，不将本地纯C#测试称为Unity相机/HTTP联调通过。

## W7.1 既有征求意见轮次 UI（2026-11-12）
- 登记跨冻结修改 RecommendationsPage：保留建议看板、原轮次矩阵与报告入口，仅接入独立 consultation 组件与局部 w7.css。
- 范围：既有轮次选择、登记回复/意见、Pending 意见采纳决定、服务器汇总与审计刷新。不新增/关闭/放弃轮次，不外发消息，不改服务合同或实现。
- 实际案件 report_draft 策略决定读写，失败/未知 fail closed；关闭轮次不能收回复，但按现服务语义仍能处理 Pending 意见。部分/未采纳必须非空反馈。
- 切案件/身份清空数据与表单，失效异步结果不回填；提交锁防双击。403/409明示并只重载读取，不自动重试写操作。结果不确定时保留错误，不假称写审计成功。
- 组件/模型自测与全web/build由实施方执行；真实HTTP与浏览器流程由独立验收执行，静态渲染不冒充交互完成。

### W7.1 独立验收准备
新增tests_acceptance/W7真实回环HTTP验收，使用临时SQLite与独立服务进程，不写生产数据库。按现有report_draft权限及closed规则验证回复/采纳、重复与失败不增审计、RO/Deny隔离、审计链及跨案数据不变；closed禁止新回复但Pending意见仍可决定，保持服务既有合同。冻结后执行并另记UI源码/浏览器与回归结果，不改后端接口。
- W7.1 冻结后重开修复：父级 RecommendationsCasePage 也按 role/operator 身份加入 key 重挂载，清空审计（含反馈）、看板与旧表单；既有 useLoad cleanup 将旧请求 alive=false，不允许旧身份读取异步回填。新增静态接线回归，实际切角色由浏览器验收。

### W7.1 身份隔离修复后的旧断言适配
整页Recommendations key由case/id增加role/operator身份，旧case-linked-pages测试固定字符串因此失败。保留原测试及断言数量，Recommendations分支改查更严格的case/id/who key和身份订阅，Evidence分支保留原case/id key；未放宽卸载旧数据/表单要求，不改实现。
- W7.1 浏览器返工：768px文档横向溢出（实际37检查中唯一失败）。局部w7-page栅格折叠、看板/操作行换行；w7.css仅对.app:has(.w7-page)修正顶栏最小内容撑宽与行高，保留侧栏/按钮/内容，不以overflow:hidden掩盖。全局styles与Layout不变。

### W7.2 独立验收准备
新增独立test_round_lifecycle_w72_http.py，复用未改W7.1真实回环临时数据库fixture，不覆盖W7.1用例。覆盖默认固定days=30/isAgreedDeadline=false、新建/已确认放弃/关闭的审计与持久化、重复和非法失败无增审计、RO/Deny权限、跨案数据不变、关闭时仍有Pending意见可合法决定。UI冻结后另验身份/异步/防双击与全web；无外部发送。后端空串/重复party及跨客户端并发open既有风险明确记录，不在本UI验收中悄悄修改合同或实现。

## W7.2 轮次生命周期 UI（2026-11-12）
- 登记修改W7.1冻结的consultation组件/model/types并新增RoundLifecycle组件与测试；W7.1冻结记录不覆盖。
- 新建仅固定默认30天，版本/各方ID与名称trim必填，ID按大小写敏感去重，草案哈希可空或规范化64位小写hex；不上传附件、不发送草案。
- 登记已确认的放弃回复事实，非替相关方作出放弃；理由trim必填。关闭前提示无重开接口且Pending意见仍可决定，客户端时间仅提示，最终由服务判断allReplied或到期。
- 三操作本地二次确认、沿用同步gate/案件身份隔离/无自动写重试。网络失败后只读核对，不声称未生效。
- 不改服务合同/实现；后端仍有空白/重复输入弱校验及跨客户端新建竞态，本UI校验不等于后端安全补齐。固定30天避免days非30却标默认30天的既有审计语义问题。
- W7.2追加受控截止时间独立验收：新增test_round_deadline_w72.py，每项独立临时DB，TestClient仅monkeypatch本轮router now_utc，deadline−1μs/等于/+1μs验证关闭规则与审计，不修改生产时钟或伪称真实浏览器时间测试；与6项真实HTTP分开计数。
- W7.2 根源码审查返工：mutation catch必须同时重读父级审计。已落库但响应丢失时仅重读rounds会保留旧审计；新增onChanged只读刷新，不重试写。首版冻结清单已按仅此一行修复前内容恢复归档before-audit-reconcile-fix（从当前文本移除明确新增行重建其SHA256，未声称是独立验收产物），更新正式冻结并重跑实现方Web套件427条/build；完整九套件由独立验收另跑。

## W7.3 征求意见输入与核心对齐（2026-11-12）
- 独立红基线8项6失败2通过，实施仅4规则：拒空白草案版本、空白相关方ID、原样Ordinal精确重复ID、纯空白放弃理由，新增handler校验在权限校验之后；错误consultation_invalid_argument/422。
- 保持核心错误优先级：版本先于开放状态检查；ID/重复检查在开放状态检查之后；放弃理由在轮次存在/关闭检查之后、相关方检查之前。有效值原样存储，不trim规范化，' A '与'A'、a与A不同；名称可空；空reason继续既有Pydantic min_length结构422。
- 不改API字段、合同、操作人/期限规则、历史数据和任何锁。撤回此前仅加外层WRITE_LOCK的建议：未外锁路由可能先持SQLite写事务再等审计RLock，与外锁路由形成逆序循环等待。reports现有外锁不是安全证明，跨路由事务锁协议另审。
- 独立验收文件不修改；实现新增自身回归测试，冻结后再独立复验。
- W7.3独立补充验收登记：另增优先级/Unicode边界测试，不改8项红基线；未知/关闭轮次先于空白放弃理由、已有开放轮先于party错误、权限先于域空白校验，空reason仍结构422。仓库外离线net8 console实际核对IsNullOrWhiteSpace，与Python验收独立，锁风险仍仅源码评审且本片不修。
- W7.3 Unicode边界：采用显式.NET Char.IsWhiteSpace字符集合，不用Python strip/isspace（后者还把U+001C..001F归空白）；加入合法控制字符与零宽空格原样保留的HTTP测试，不扩展拒绝范围。
- W4.1独立验收准备：新tests_acceptance/W4覆盖case-scoped inline CSV预览安全边界；临时SQLite、自己创建的非敏感canary、调用spy及真实本地DLL分层记录，不修改实现。冻结前仅准备，真实执行结果另记；不把旧/core/align入口风险称为已修复。

## W4.1 案件级 inline-only align 临时预览（2026-11-12）
- 先新增typed schema/OpenAPI再实现新POST /cases/{caseId}/timeline/align-preview。仅内联CSV及显式列映射，逐层strict/extra forbid；固定align命令，不接受caseId/epoch/command/path/manualAnchors/未知参数。案件与纪元由服务load_case读取，timeline read权限足够，关闭只读session后计算。
- 工程预算：最多4源，每源文本256KiB UTF8、总1MiB，每源16列，源ID64字符、列名128；非空/源ID唯一。kind限Heading/CourseOverGround/SpeedOverGround。CSV逗号、UTC（无offset按UTC）、scale1/offset0；使用者明确保证时间为UTC，不猜本地时区。calibrate=true，无锚点/未校准状态及错误必须显示，不承诺成功校准。
- 响应明确previewOnly/persisted:false/current case与epoch，校验结果案件和全部冲突schema。未知基础设施错误不回显路径/stderr。无持久化、审计、冲突采纳或人工复核覆盖；旧裸/core/align完全不改，不能把新代理说成整个服务路径漏洞已修。
- Evidence整页身份/案件重挂载失效旧数据、表单和响应；独立局部预览面板读取实际policy，失败禁用，RO可预览。修改已冻EvidencePage需后续全web/关联页回归；如静态断言与新身份key冲突仅强化改写，不删测试。
- W4.1关联页静态断言按原规则强化：Evidence和Recommendations均要求case/id/identity key，不删除原断言；相应test文件纳入新冻结。此为新增整页权限隔离接线，不改变原报告引用目标逻辑。
- W4.1局部响应式：Evidence原两列/六指标改局部class，w4.css只对当前路由折叠及顶栏换行，保留所有内容；不改共享styles或旧写操作。
- W4.1根布局审查返工：预览长表单不能默认挤走原证据KPI/清单。Evidence仅将新增工具包在原生details默认收起，summary『临时CSV预览，未入库』；展开后原计算/权限状态不变。原13项冻结保留before-collapse，重跑web/build后重新冻结。

## YANGZE canonical source pin correction（2026-11-12）
- 独立红基线已确认：本地首次物化原文末尾误多一个LF，使错误62608byte/7adad5bb…被误pin三处；远端原文从未改变。父已保留错误副本并恢复canonical，实施不再改原文。
- 唯一canonical：reports/yangze22/report.txt，commit c6113bee85d25bf97d805fb2d264fb6ab138b2e2，62607bytes，gitblob d5a6b5fc79ad0371c8ccc372b40ca9110d5c30c4，sha256 bca8f8b8ba04a5d0669a121bc6c9380c8cd6f8397f67be2d0b30b38871c22ef2。修seed/public_text/templates三pin，严格拒旧多LF副本，不normalize或双hash兼容。
- 独立hardcoded SHA/size/blob回归及freshDB验证；既有DB的错误EV-201/原始blob/保管链不自动重写，不伪造来源一致。历史DB修复需要另立合法证据更正/迁移流程。
- 历史日志/冻结原样保留，但其中以错误多LF物化文件通过的来源校验、freshstartup及引用验证不能证明canonical可用；本次生成新manifest与独立重跑。manifest含canonical原文仅验证输入，不作为远端文件改动项。


## HTTP core error redaction (2026-11-12)

Scope: colreg.router._core error responses only; documented in contracts/CONTRACTS.md. Known error codes/statuses remain stable with fixed safe messages; unknown CoreError codes collapse to CORE_ERROR/502. CLI and successful HTTP responses are unchanged. No source files frozen by W4.1 are modified. This does NOT remove the old /core/align path-reading capability or implement authentication; disabling/restricting that documented route remains a separate compatibility proposal. No database migration, merge or deployment.

## Core envelope type validation (2026-11-12)

Follow-up to HTTP error redaction: validate only the envelope types consumed by Python core_client (object, boolean ok, object result/error, string error code/message). Malformed output becomes CORE_BAD_OUTPUT/502 rather than incidental AttributeError/TypeError/500. Valid success envelopes and domain error mappings are preserved, including default fields in an empty error object. CLI, case authorization, filesystem path capability and authentication are unchanged. No broad exception catch, migration, merge or deployment.

## W8.1 案件大厅最小闭环（2026-11-12）
复用 GET /cases 摘要合同；不新增后端接口。不包含新建、编辑或 .mcase 导入导出。修改共享 Layout/caseContext/main/routes 接入列表与案件切换；仅已支持案件上下文的页面保留 case 参数，Outlet 按案件与身份隔离重新挂载，防止旧页面状态跨案残留。未知/未加载的案件不标为真实报告来源。独立验收前标记待测。

## W13.2 proposal: reject malformed new replay intents before queue insertion
Against main b6fc86c. Cross-package edit: service sim/router.py and contracts/CONTRACTS.md. Existing command schema is permissive; tighten new POST /sim/commands inputs to the already accepted ReplayCommandAdapter parameters. This intentionally changes malformed requests from 201 to 422. Keep all valid wire payloads, state telemetry rate range, historical command rows, audit history, cursor/ACK/restart behavior unchanged. A focus callback may still be unavailable or fail: this validation is not a delivery or execution guarantee. No remote publication or merge in this review task.

## CPA series bounded sampling (2026-11-12)
Security/availability fix against main c54990c: only case-scoped GET /cpa time sampling changes. Reject non-finite fromSec/toSec/stepSec, non-progressing floating-point increments, and a tolerance-expanded grid exceeding 5001 samples with existing BAD_RANGE/422 before track interpolation or core invocation. Preserve finite valid grids, cumulative stepping, three-decimal rounding, 1e-9 endpoint tolerance, and the existing 5000-interval admission check. No clamping to case duration, CLI or raw align change, authentication claim, persistence or deployment. Cross-package contract/router edit registered before implementation.

## Core JSON finite-number boundary (2026-11-12)
Follow-up to core envelope type validation: Python's JSON decoder accepts NaN/Infinity tokens and overflowing numeric literals (1e309) that cannot be safely serialized by the HTTP JSON response. Reject these anywhere in the final core response envelope as existing CORE_BAD_OUTPUT/502 before downstream use. Preserve all finite JSON numeric values, integer decoding, string values, extra fields, build preamble/last-line protocol and valid domain error mappings. No input limits, CLI changes, schema shape change, authentication, raw align restriction, persistence migration or deployment.

## 2026-11-12 W8.2 案件新建闭环

沿用现有 POST /cases 合同和 case.schema.json。新增表单/纯校验，修改 W8.1 冻结的 LobbyPage.tsx、w8.css（以及确有必要的 cases/model.ts）以开放新建；保留只读列表能力。规格见 contracts/W8.2-case-create.md。不得改公开报告、历史种子或服务权限规则。旧冻结保留，新切片单独冻结与验收。选择本片是为了让空安装从只读演示升级到能创建自己的调查案件，不声明整个 W8 完成。

W8.2 入口联动追加：现 Layout.tsx 将所有虚构案标为 Lily/Mary、所有非虚构案标为公开报告。新建案件不能继承虚假来源，故将既有 W8.1 冻结的 Layout.tsx 纳入本切片，用实际标题及保守虚构/非虚构标识。不能在无证据时声称“公开报告”。

### W8.2 D01 独立验收返修

独立验收发现 EvidencePage.tsx 仍将所有非虚构案件主标题标为“真实案例（公开报告）”。按架构裁定，将 W4 已冻结文件 web/src/pages/EvidencePage.tsx 纳入本片，仅修改案件标签为保守“非虚构案件”并展示实际案件标题；不改证据数据、时间轴或任何写入逻辑。原 W8.2 冻结保留为 logs/w8.2-impl-hashes-frozen.v1.txt，返修后重新冻结；独立测试保持不动。

### W8.2 空案件显示收口（D01 后续）

新案显示时区为 UTC，但 EvidencePage 全部时间显示与标题仍硬编码 UTC+8，且空证据显示永久加载、任意虚构案借用 Lily/Mary 演示时间线。按架构裁定，允许 format.ts 增加可选显示偏移参数（默认480，保持其它页面行为），EvidencePage 所有时间显示传入当前案件偏移；新案无证据明确显示暂无证据，专属 Lily/Mary 船名/时长/碰撞标记仅限 CASE_ID 演示案。仅修显示，不变更事件时间、存储或计算核心。旧冻结v1/v2保留，全部修改后一次性再冻结。

最终采用架构补充裁定：时间显示 helper 位于 web/src/cases/evidenceTime.ts，仅由 EvidencePage 使用；共享 format.ts 保持原始字节不改。此前可选参数提案未进入最终实现，避免其它页面回归。

## 2026-11-12 W5 案件上下文隔离切片（实现前登记）
基线 main 0a29f28。修复 InterviewPage 固定 CASE_ID，接入 ?case 和全局导航；按案件/身份/笔录切换销毁旧选择、表单和请求结果，所有读写显式编码案件与记录 ID，防重复提交和迟到通知。空案不借用演示笔录，非虚构案不擅称公开报告。只动 W5 页面/视图和 caseContext 路由白名单及相关测试；不改后端合同、其它包实现和报告/核心。保留默认演示入口。W5 时间显示仍沿用现有 UTC+8，本切片不宣称完成所有时区改造、笔录创建导入或生产认证。不部署。独立验收后才合并。
W5 同步必要修正：服务 W5 roster/detail disclaimer 只对固定演示案标 Lily/Mary，其它虚构案为通用虚构声明，非虚构案为保守“非虚构案件”，不从布尔值推断公开报告来源。字段/合同不变，新增 HTTP 回归。此前7项初稿冻结保留为 v1，正式独立验收以新清单为准。

## 2026-11-12 W9.1 船舶录入限定切片

合同先行登记：W9 原路线图 03 船舶参数的首片，仅案件级新增静态参数、保存、重开与来源显示；不覆写/删除已有船舶，不做环境/操纵曲线/模型自动抽取/部署。新增 POST vessels，原 GET 不变；vessel schema 增加可选 parameterSources，旧记录仍有效。新写入校验与来源规则见 contracts/W9.1-vessel-entry.md。跨包仅 cases/router.py、共享 openapi/schema、main/routes/caseContext 接线；其余新文件隔离。既有冻结按原包片段核对，不重冻结旧包。

## 2026-11-12 W8.3 限定 UI 切片登记

原型大厅打开 .mcase / 分析页导出与 ARCHITECTURE §11/R-03 为依据。W8.3 在已验收 W8.2 LobbyPage 增加预检工具、按卡片案件ID导出，不改旧建案/来源/时区逻辑；共享入口 main/routes、服务、现有合同、W9/W20不改。新增规格 contracts/W8.3-package-ui.md；预检仅清单哈希一致性，不是真实性、审计链或导入验证。导入因既有非原子文件写入与资源预算缺口暂不开放。新样式独立 w8-package.css。旧冻结保留，旧LobbyPage漂移仅核对本切片接线，新清单另列。

## W20.1 本地 LLM 抽取最小切片（2026-11-12）

依据用户重新强调的真正 LLM 驱动设计，优先落地 ARCHITECTURE §15.5 人员/作业文本提取。接口先行见 `contracts/W20-local-extraction.md`。增加本机 OpenAI-compatible 模型适配、严格逐字引用校验、PendingReview 与人工确认追加陈述；保持默认禁用，其他五角色不连接，不引入外部模型、密钥或部署。
跨包只追加 `contracts/openapi.yaml` 路径及专属 schema，不修改 W5 `interviews/router.py` / InterviewPage / caseContext，不修改 W9 船舶与环境接口。保留 interview schema 和 UTF-16 SourceSpan，不复用不可靠的脱敏后偏移。多模态证据是后续目标，本轮不宣称 OCR/ASR/视频处理已接通。

W20.1 最终集成：W5、W9、W8.3 精确主线 03e3fb8 的已有改动与共享记录全部保留。独立发现三项边界缺陷后统一返工并再次冻结；服务全量603、独立组合95、最终相关回归102通过。仅提交 agents 层、专属契约/测试/说明及共享追加，不触碰 Web。实际本地模型尚未提供，不能将协议假服务验证称为真实推理；后续真实模型与多模态评测是单独工作，不阻塞这条已验证的受控人审代码链路。

## 2026-11-12 W10.1 航迹只读检查登记
原型05/ARCHITECTURE§4.2/track-point合同依据及边界见contracts/W10.1-track-inspection.md。本轮只读已存航迹与来源/时间描述，不做无接口支持的导入/编辑/保存成功UI。新增TrackPage/tracks/w10.css；共享main/routes/caseContext只增加track接线和已实现只读文案，不改W9/W20业务或服务。共享文件不入单包冻结，旧冻结不改。

## W20.2 笔录抽取与人审 UI（2026-11-12）

基于已合并 W20.1，以 `contracts/W20.2-review-ui.md` 为先行规格，W5 `InterviewPage` 仅嵌入专属面板并在确认后刷新原有陈述。新增 agents 前端模块与独立样式/测试，既有服务、身份头合同和导航不改；不与 W10 共享 main/routes/caseContext。逐条来源与语义核查后确认，驳回须理由；不做 Modified 编辑器、不扩接其他五智能体，不部署。模型配置、实际连接与推理能力分开表述，无真实本地模型时仅合成 HTTP 假服务验收。
W20.2 最终组合以 W10.1 main `8fce05a65b3df0364819207d749c50ce6f86be8b` 为基线，36条变更逐blob核对并保留共享追加；不改 W10/全局入口/后端。独立限定验收通过，真实模型质量仍未验，不混同协议假服务测试与推理能力。



## W9.2 环境观测记录跨包登记

按 W9 原设计新增独立环境观测合同、案件级追加存储和 UI，保留未知与来源口径。修改 service main/models_registry 接线、OpenAPI、package/mcase.py 可选环境记录往返以及 Web main/routes/caseContext 接线；保留 W20.2/W10.1。无专业阈值、仿真接线或部署。实现边界见 contracts/W9.2-environment-observations.md。

## W19.1 知识卡初始切片（2026-11-12，实现前）

合同先行见 contracts/W19.1-knowledge-cards.md。新增全局公开/合成Case/Challenge/Method候选→首席人工明确发布/驳回/撤回→结构化字面检索；不从案件自动导出，不做向量/LLM/训练/分级通知。独立模型/路由/审计表与前端，原表/权限不改；共享注册限 service main/models_registry、web main/routes、openapi与本记录，W9线发布后按精确基线串行整合。只有来源分类不构成发布许可，额外明确人工来源/使用权/发布范围审批；哈希不是真实性证书。不部署。
W19.1 数据边界补记：这是全局人工资料库，不属于任一案件卷宗；当前 .mcase 导入/导出仍只处理案件，不把知识卡或其独立审计链混入案件包。已发布内容能撤回后续访问，但无法追回此前用户读取或另存的副本。没有自动认定链接/摘录真实性或数据训练许可。
W19.1最终串行集成：W9.2 main `2bdbeb4f2fbe9eece6c0167274d1caed25495824` 的main/models_registry、Web入口/导航、环境与案件包/OpenAPI及所有记录保留，W19仅重放已登记新增项。共享注册变更重新冻结并独立复验，来源/许可与公开审批边界不变，具体证据见logs/w19-verification.md。


## W8.4 案件文字档案编辑

独立 case_metadata router 与 #/case 页面，五个文字字段编辑、版本冲突保护、来源理由与完整前后值审计；时间/坐标/分类/虚构性质锁定。合同先行见 contracts/W8.4-case-metadata.md。跨包仅 main router接线、OpenAPI及 Web main/routes/caseContext与大厅说明；不改cases/router、W10导入/W19实现或原始报告，既有案件包字段往返不变。

W8.4 共享壳补充：Layout 目前仅在切案/大厅时读取标题，保存文字档案后会显示旧标题。允许新增案件定向 metadata-changed 通知并让当前案壳重新读取，防迟到/跨案，不修改通用API或虚构性质。此项列入UI独立验收。

## 2026-11-12 W10.2 合同先行及共享接线登记
基于main8235918按原W10继续明确语义UTC CSV首次输入，范围见contracts/W10.2-track-input.md。读取原型、ARCHITECTURE§4.2和现C#解析/清洗实现后，限制为显式字段状态交换格式，不把普通102.2数值推断为AIS饱和，不暴露未验证的NMEA/清洗链。新增独立tracks_import与trackInput模块；改TrackPage接线与routes航迹副标题（避免整个页面仍称只读），main.py注册路由，openapi新增接口。登记W10.1 TrackPage冻结预期漂移，旧冻结保留。W9并行W8.4由双方串行整合，不改其caseEpoch/元数据逻辑。尚未实现验收完成，不部署。

### W10.2 D01 恢复核查返修
独立验收37场景36过1红：隔离数据库故障注入删除已存点后历史导入回执仍200。不是正常操作已证实丢点，但未知写结果恢复UI可能误认完整保存；裁定必须重算原件/配置绑定并核当前全部点，缺失/多点/内容或纪元变更409失败关闭，不自动修复。保留v1冻结及原红测试，返修后整套独立复验。未发布。

W10.2 串行整合以 W8.4 main `7c1208daef26fd263b87edd9d06bab3d6b267725` 为准，35条远端变更逐blob核对保留。W8.4共享OpenAPI/main.py整文件冻结因已登记W10路由追加预期漂移，剥离W10专属新增后与W8.4原文逐字一致；不改旧冻结。W8.4业务合同/实现与10项UI冻结不变，独立组合重验另记。本轮没有改caseContext/Layout/Lobby/metadata字段规则。

## 2026-11-12 W4.2 数字文件副本登记切片（实现前）
以W10.2 main096e3d2为基线，依据原型09/ARCHITECTURE R-03及NIST IR8387/SWGDE/IMO已核资料，先行合同见contracts/W4.2-evidence-intake.md。仅已获得文件的副本保全，已知UTC整秒提取人/时间必填，默认Restricted并确认；8MiB是工程上限，不代表业务标准。新独立evidence_intake/evidenceIntake，现有Evidence/Custody Register.detail存请求元数据，避免新增表/mcase扩展；共享main/OpenAPI接线，EvidencePage只嵌入面板并刷新清单。W4.1/旧W8.2 EvidencePage冻结预期接线漂移，旧冻结保留。与W11按精确主线串行，不碰其图/核心/包实现。无真实文件上传、钟差或多模态解析、部署或生产认证承诺。

W4.2 D01裁定：独立网络故障复现关闭表单主动abort已发commit，发生于服务器读请求体前，不是已落库后撤销。新面板commit与可取消读取分离；SPA关闭/导航只失效UI，网络/整页终止结果仍可能未知。保留旧freeze及红用例，返修新冻结后完整复验。

## W8.5 restricted basic package intake
Contract: contracts/package-intake-v1.md. New isolated backend/frontend; shared changes
limited to main router registration and Lobby entry. Existing import/export unchanged.
Only new cases, strict supported subset, original archive retention, explicit commit,
GET-only unknown-outcome recovery. Independent acceptance required before completion.

## W17.1 权限只读核验
原计划17号工作台小切片，合同见contracts/access-workbench-v1.md。
新独立access_workbench后端和accessWorkbench前端，主router/main/routes最小注册。
仅逐案授权读取策略与最近策略更新记录；不改旧权限API、不修改策略、不宣称生产认证或脱敏实施已完整。

## W18.3 工休基线预览
核对官方STCW/MLC原文及既有W18.2算法后，限定非结论性技术预览；合同rest-preview-v1.md。
独立mcis-rest工具引用既有不变RestHours/Result源，防止改动原core DLL造成W12来源漂移。
13号页与新只读计算/来源端点，不写已确认事实、不自动补休息、未评估专业适用条件明确展示；仅合成验收数据。

## W15.3 假设 Bow-tie 结构预览
合同先行：contracts/bowtie-preview-v1.md、schema 与 OpenAPI。新增独立 CLI、只读服务与 page14，修改共享入口 main.py/main.tsx/routes/caseContext；不改原核心/W11。仅待核验人工假设、Unknown屏障，元数据来源绑定不等于事实支持。原型其余 AcciMap/STAMP/ECFC/导出/持久化不在本切片。

## W14.4 假设单船恒舵响应预览
新增合同/schema/OpenAPI、隔离mcis-nomoto工具与page12子集，修改main.py/main.tsx/routes/caseContext共享入口。引用原核心不改核心，不接W11。参数必须人工提供，输入来源/不确定性说明必填；两条航迹均假设。碰撞/临界/多船/锚泊/完整What-if未实现，零安全结论，不部署。

## W18.4 人工分类草稿持久化
合同/schema/OpenAPI先行。新增独立Hfacs CLI、case-scoped worksheet/audit/request表、main与models_registry注册、HFACS pane；保留工休预览及PR25边界修正。人工选择仅待核查，不作证人/人员过错或责任判断；目录为项目版本而非统一海事标准。固定Draft/ToBeVerified/Investigator，不连接确认/报告/ECFC，不触W11。原子事务+版本摘要+幂等收据，审计权限独立，不部署。

## W18.6 HFACS完整案件包备份扩展
合同见contracts/hfacs-package-extension-v1.md。跨包修改package/mcase及导出权限事务、package_intake严格预检/恢复、hfacs_drafts归档回执model和保存ID占位、models_registry注册。完整当前/审计/回执不截断；回执不可重算原摘要，只归档不活化。新案默认权限恢复，旧入口拒扩展，不改核心/W11/web，不部署。

## W16.2 conservative full-report access boundary
Contract: contracts/report-content-access-v1.md. Approved scope includes reports, report-bearing generic audit/history and package export; explicit SQLite authorization transactions and no-store. Default Investigator compatibility intentionally restricted, without policy changes. Full content access is not redaction or authentication. Synthetic-only tests; no W11 or professional template/core edits.

## W5.2a interview full-content access isolation
Contract contracts/interview-content-access-v1.md. Existing routes restricted: interviews/compare/redaction preview, related agent drafts/application, audit and package paths. Default Investigator loses original-content access without any policy changes. SQLite writer serialization prevents lost question/answer updates. Old creation becomes unsigned empty draft only; signed records are immutable via these endpoints. Legacy transcript package import rejects rather than restoring permissive policy. W5.2b manual idempotent entry remains separate; no W11/core edits.

## W5.2b manual interview entry
Contract contracts/manual-interviews-v1.md. New create/append/current/recovery endpoints with requestId receipts and full-document optimistic digest, same original InterviewRow. W5.2a security applies. backupAcknowledged software notice required; any receipt blocks old case-package export before side effects, even if record is gone. No signature/identity or factual verification claim; no W11/core changes.

W5.2b record reservation hardening: approved cross-package change to legacy interviews.create: receipt-referenced IDs remain reserved when original row is absent, including automatic allocation. Explicit reuse409; prevents orphan receipt recovery pointing at a replacement transcript. No alteration of existing original record or receipt.

### W5.2b reviewed shared lock-order correction
Approved narrow shared changes: reports/access.py marks only successfully acquired SQLite BEGIN IMMEDIATE with root transaction/connection/thread proof; audit/service.py avoids inverse Python lock acquisition only for that verified active root writer (including its savepoints). Existing unmarked and non-SQLite calls retain prior locking. No change to professional core or W11. Tests cover real manual/legacy/compare/export interleavings, proof lifecycle/fallback, rollback and actual independent-process reserved writers. No raw SQL COMMIT/ROLLBACK found in service source; such driver bypass and shared-session cross-thread use remain unsupported.

### Archive safety A: refuse known incomplete exports
Authorized narrow package export correction, following synthetic reproduction: ReportRow/ReportAuditRow export200 omitted documents; legacy InterviewRow export200 could not be restored (422). Preserve existing permission and source checks, then reject known report/interview records or residual classified audit with409 ARCHIVE_RESTORE_UNSUPPORTED before files/export audit. Preserve dedicated manual receipt refusal. No import, shared lock, core/W11 or database content changes. See contracts/archive-export-safety-v1.md.

## W19.2 来源模板整理预览（2026-11-12）
登记跨包/已冻结改动：knowledge/router.py、KnowledgePage.tsx和共享openapi.yaml；仅追加只读预览、保留W19.1创建/审批/审计。新合同W19.2-suggestion-preview.md先行。不触及W11及笔录/报告。采用受控模板stub，未接LLM，不代表自动知识理解已完成。

## W20.3 只读智能体协作状态（2026-11-12）
登记新前端模块agentOverview及AgentOverviewPage，新合同规格W20.3-agent-overview.md。共享接线main.tsx、routes.ts、caseContext.ts仅新增agents路由并保留案件上下文；不修改其他模块。只调用既有GET agents/drafts，主会话/任务编排尚未实现，无假聊天或自动执行，不碰W11。

## W7 原文访问隔离 v1（2026-11-12，先于 W7.4 UI）
纯合成确认默认 Public 可读取建议 Draft 原文。经授权按既有报告/笔录保守 full-content guard 修复，不改权限矩阵。登记跨包 Recommendations router、audit router、access_workbench router（原始审计行分类门，保留核验内容）、package/mcase.py；新增 recommendations/access.py 和合同 recommendation-content-access-v1.md。覆盖建议/征求意见读写返回、派生审计、组包前准入及旧导入目标库权限，不触 W11。默认 Investigator 收紧为403，明确兼容变化；共享包与归档B串行重放窄改。无 CAS/回执或可靠正文编辑宣称。

回归断言适配：test_recommendations 使用已授权首席和纯合成种子保留原业务断言；test_reports_w162_access 保留旁路用例但默认 Investigator 的 history 未授权先403，不再先查存在404。

### Working-record archive B: reviewed bounded restore and compatibility changes
Independent contract review approved working-record-archive-v1.md before implementation. New1.2 extension restores complete supported interviews/reports/snapshots and inert receipt/source history; unsupported tables/files/citations remain whole-export refusal, never fallback partial success. W11 and professional core unchanged.

Intentional compatibility boundaries: a restored case now has source.mcase/intake history, so its subsequent full archive requires full12 original-content permissions. Default Investigator previously exporting narrow HFACS/basic or evidence-only packages must now receive403 when such working/import history is included; qualified Lead tests retain original restoration assertions plus explicit Investigator403. Evidence-intake restored receipts no longer reactivate; existing replay/download entry points return409 ARCHIVE_HISTORY_ONLY, while authorized history content preserves original bytes and appends a new Access event. Old generic import cannot accept1.2. Existing fault-injection tests now verify safe500/no-store plus unchanged DB/blob state because NoStoreRoute deliberately does not expose internal exceptions.

Manual original A refusal applies when a case remains unsupported/incomplete; a complete validated1.2 package can now preserve active/orphan manual receipts as inactive history. Forced writer/export interleaving asserts actual complete snapshot contents (not merely changing an expected status). Entire new package processing runs in worker helpers after bounded async body reading; SQLite sessions remain owned by one worker. Export422 semantic preflight failures map to409 ARCHIVE_RESTORE_UNSUPPORTED;403, budget413 and failure rollback remain intact. No user-visible completion is claimed until independent acceptance.

W archive B compatibility: legacy packages containing evidence-intake custody credentials without a validated working-record extension now fail closed at import. This concerns subsequent imports only; existing database credentials are not migrated, cleaned or silently rewritten. Version downgrade/incomplete namespace attempts are tested.

## W7.4 安全建议只读核查（2026-11-12）
登记已冻结 RecommendationsPage.tsx 的窄接线：新增独立 recommendationReview 正文/全部已登记回复读取器及可选单建议审计；合同 W7.4-recommendation-review.md 先行，使用原有 GET 与服务端权限。无后端/schema/共享路由修改，不修称旧写并发，无正文编辑、自动状态变更或外发，不触 W11。审计现接口最早至多 200 条，不宣称完整审计链。

## Knowledge archive v1: independent historical collection (2026-11-12, implementation in progress)

User requested enduring structured investigation datasets and reliable recoverable records. This slice is intentionally separate from `.mcase`: preserve all currently stored W19 card documents/index columns/original audit strings, and future complete create/review snapshots, in a bounded versioned JSON envelope. Lead-only save creates immutable read-only history, never online cards or reactivated approval. Historical Published is not a present release decision. Existing Withdrawn cards have already overwritten publication approval fields; no old missing fields are reconstructed. Snapshot coverage starts explicitly with the first new writer transaction and retains the prior original chain hash.

Cross-module agreement: three exact global non-case tables (`knowledge_archives`, `knowledge_audit_snapshots`, `knowledge_audit_snapshot_epoch`) may be added to the working-record archive GLOBALS exclusions after confirming no case_id, case foreign keys, or case retrieval. This preserves existing `.mcase` scope, not broader backup completeness; unknown nonempty case tables still fail closed. Free-text privacy/public-source truth cannot be guaranteed by a Public/Synthetic label. All original source/review labels are self-reported; hashes only check internal consistency. New library exports exclude saved history collections, whose exact original files remain separately retrievable.

Contract: `contracts/knowledge-archive-v1.md`; design-only independent review: `tests_acceptance/KNOWLEDGEARCHIVE/PRE_REVIEW.md`. Runtime implementation and independent acceptance remain outstanding. No W11, deployment, online restoration, automatic disclosure, model call, or candidate derivation.

### Archive B uniform OpenAPI omission

Unmodified baseline W19/W19.2 suite reproduced 65 pass / 1 route-contract failure: PR36's two real archive-history GET routes were described only in the dedicated fragment, absent from shared OpenAPI. Added their shared declarations and removed stale implementation-pending prose; no runtime routing or behavior changes. Same 66 tests now pass (9.20s), original red assertion unchanged. Independent route test passes, and two isolated synthetic databases produced actual restored provenance JSON conforming to both declarations plus exact historical bytes/headers. This is contract integration correction, not a new runtime restoration claim.

## W10 restored receipt isolation (2026-11-12, implementation in progress)

Real synthetic stage demonstration on released main d44bb4e found that restored W10 digest GET, vessel receipt list and identical original-body commit returned active `replayed:true`. An independent empty-database reproduction confirmed all three; raw originals were preserved, so this is a current-operation provenance/receipt defect, not a claim of byte loss. The demonstration remains failed until the unchanged receipt-isolation assertion succeeds.

Approved contract `track-history-v1.md` reserves package1.3.0 / working-record root v2 (single existing member path) when W10 is included. Original CSV/report and chains remain exact; imported receipts become separate inert history indexes. Old W10-containing1.0/1.1/1.2 top-level imports refuse without writes; old no-W10 formats remain supported. Do not label unsupported migration as corruption or delete a user's old package. W7's unimplemented proposal moves to a later version; no W7 or W11 work is included.

Previously restored databases cannot reliably be distinguished from genuinely local old receipts. The intentional conservative upgrade introduces append-only local commit markers made only by new real commits, never by import/backfill. No marker and no historical index means TRACK_ORIGIN_UNVERIFIED, not proof of failure or permission to retry with new IDs. Existing source data remains; strict validation may export1.3 for archive-only restoration. Local markers are non-transferable runtime-origin state, not identity authentication; their portable business contents remain in original report bytes/indexes. Orphan/conflicting markers reject export and keep both evidence IDs/digest reserved.

W10 only adopts existing WRITE_LOCK then actual SQLite BEGIN IMMEDIATE in a synchronous worker, with marker/points/evidence/chains in one transaction. Shared locking framework is unchanged. Actual two-process and rollback tests required; no arbitrary crash-atomic or systemwide multiworker claim. History byte reads require current full original-content permission plus both source registrations and commit Access before returning bytes. UI must separate active/history/unverified and never clear unknown current write state on the two history/source-origin refusals.

### Independently verified legacy provenance limitation

A genuine pre-fix1.2 restricted restore with saved report remains readable after upgrade (report GET200), and its preserved current state can validate/export1.3 and restore into a new empty destination. However, the old database's latest-restore provenance lookup still uses its original W10-containing1.2 source package and returns409 ARCHIVE_HISTORY_UNSUPPORTED with an explicit old-version compatibility explanation. Only the exact structured legacy-W10 migration refusal maps to this code; actual source hash/receipt mismatches and other parsing failures remain ARCHIVE_HISTORY_INTEGRITY. This is an unsupported legacy provenance-inspection path, not proof that original bytes were tampered with or lost. No automatic rewrite/migration of the original source package or historical metadata is performed. Current report data remains; use the explicitly verified export/new-case recovery path rather than assuming the old history badge was fully migrated.

## Reproducible local synthetic stage demonstration

Continue Sunday's runnable framework goal with a deliberately limited, repeatable Linux demonstration, not deployment or production authentication. Three owned empty SQLite/loopback services execute actual HTTP case creation, evidence and fixed-UTC track input, manual interview/Q&A, template report and explicitly simulated review, restricted package1.3 empty-target restoration, and separate knowledge-history archival without online activation. Original documents and bytes are compared; restored W10 receipts must refuse active replay. No W11, LLM, real accident materials or installation is involved.

The first pre-fix demonstration failed on restored W10 active receipts, leading to separately verified PR39; the failing baseline was not relabeled passed. The post-fix runner and real read-only browser now cover the selected flow. API scripted writes are not claimed as complete UI form entry; authorized history downloads append Access audit. A normal --hold SIGINT exit stops only owned child processes. Stale manifests or another PID namespace fail closed; external forced termination can leave stale running state. Independent review found optimization could remove assert-based checks; both tool entrypoints now explicitly reject optimized Python before outputs/services. Three existing UI notices receive only precise1.2/1.3 wording corrections, not broader restore semantics.


## Report output A: explicit traceable client download, not server retention

Investigated the confirmed gap: existing report.export keeps format/language/SHA and operation snapshots, not the streamed original PDF/DOCX bytes. Ordinary EvidenceRow registration would not supply equivalent report-content permission checks, and new retention tables without simultaneous versioned archive support would regress backup behavior. Therefore implement the approved independent A slice only, with a separately marked deferred B plan.

Users explicitly preview the currently saved report, choose one format/language and confirm one generation. A four-member ZIP contains that single actual PDF or DOCX, canonical exact report input JSON, the original export audit line and operation snapshot, and an unsigned manifest. Existing reason text binds report/output hashes into the original audit; no new persistent bytes, table, active receipt, import format or case-package version is introduced. Re-generation is a new output, not recovery of identical lost bytes. The user must save the downloaded package.

The new endpoint adds conservative current-case evidence/interview visibility and row/document binding checks in addition to the full12-category report/audit gate. This is not a citation closure or original-source authenticity check. Render once outside transactions; short transactions before and after recheck report/policy fingerprints and permission. Preparation failures roll back the event; a post-commit delivery error may retain an audit record. Original report and ordinary export behavior remain unchanged. All generated/test content is synthetic.

The browser uses a fixed-profile ZIP_STORED and strict JSON verifier, actual member CRC/SHA, preview/request binding and original audit association. No object URL/download occurs until checks succeed. Unknown delivery persists only scoped metadata and never auto-retries. Explicit stop-wait discards even abort-ignoring late replies. After checking downloads the user can knowingly abandon an attempt and freshly preview a new generation; storage corruption/unavailability has an explicit scoped recovery check, never silent lock deletion or false success. Local headers and hashes are not authentication, signature, facts or complete audit-chain certification.

Engineering caps are declared for report/output/audit/manifest/ZIP. A self-review removed an unintended2MiB policy-fingerprint limit by streaming its hash without adding a policy editing restriction. OpenAPI labels now match the two new report-output routes while preserving the old14-report-route test unchanged. The B retention plan allocates no archive version and remains unimplemented.

## Evidence registration failure feedback (2026-11-14)
Fix scoped workbench handling only: INTAKE_INTEGRITY409 can describe a pre-existing
registration whose stored bytes fail verification, so must not clear original request
or imply no save. Unknown outcome stays locked through later denials/conflicts;
read-only recovery404 cannot authorize retry. No service writes/retry/cleanup changes.
Freeze scope: evidenceIntake/api.ts and EvidenceIntakePanel.tsx plus targeted tests.

## Evidence refresh recovery (2026-11-14)
Based on d1a4424: scoped sessionStorage recovery marker before dispatch, metadata only
(case/digest/content digest/length); refresh permits only explicit receipt GET. No file,
statement or operator persistence, no automatic resend/delete, no server/schema change.
Storage corruption/unavailability fails closed. Session-only convenience, not global
idempotency, authenticated identity or cross-tab/crash durable request guarantees.

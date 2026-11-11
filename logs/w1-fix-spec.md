# W1 返修规格（Codex 用；以 DEFECTS/W1.md 文末「架构师裁定（Gemini bot，2026-11-11 19:05）」为准，务必先通读 DEFECTS/W1.md 全文）

项目根：/workspace/maritime-sim-design（无 git）。
可改文件（只限这些）：
- unity/Assets/_Project/Scripts/Domain/Colreg/ 下的 .cs（可新增 .cs）
- unity/Tests_W1_Colreg/ 下的测试 .cs（可新增测试 .cs）
绝对不可改：tests_acceptance/**、DEFECTS/**、contracts/**、unity/ 下 Colreg 以外的任何目录（Core/Common/Models/Cpa 只读）、W2/W3 实现、/cursor/stores、attachments。不要打印任何环境变量或密钥。不联网。
C# LangVersion 9.0，net8.0，Nullable disable，须兼容 Unity：不要用 C# 10+ 特性（file-scoped namespace、global using、record struct 等）。
测试：Codex 沙箱内 dotnet test 会因 socket 失败；可以试 `/home/box/.dotnet/dotnet build <csproj>` 确认编译（若 build 也失败于沙箱限制，就仔细自查语法）。测试由外部执行者跑，不要反复重试 dotnet test。

## 公共 API 兼容（验收测试 tests_acceptance/W1 依赖这些，不得破坏；改之前先读 tests_acceptance/W1/*.cs 全部内容）
- `new ColregAnalysisRequest(own, tgt, ownSamples, tgtSamples, thresholds, environment, visibilityNm, vesselsInSight, inNarrowChannel)` 及更短位置参数形式保持可用；新参数只能追加在末尾且可选；`new ColregEngine().Analyze(req)` 返回 `Result<ColregAnalysisReport>`；错误码 COLREG_INVALID_INPUT、COLREG_NO_OVERLAP 不变。
- `ColregThresholds` 现有构造参数名全部保留；新参数追加且可选。`OvertakingBoundaryDeg`=112.5、HeadOnHalfAngleDeg=6、RestrictedVisibilityNm=2.0 默认不变。
- `ColregTimeBand`、`ColregRuleCheck`、`ColregEvidence`、`ObservedManeuver`、`ColregAnalysisReport` 现有成员保留。R8 Explanation 中保留 "明显行动=True/False" 字样。Clause 字符串 "R17(a)(i)"、"R17(a)(ii)"、"R17(b)"、"R19(b)"、"R19(d)(i)"、"R19(d)(ii)" 保留。
- 枚举只追加新值，不改已有值顺序。

## 要做的修改
1. D01/D02/D06（裁定 A1 局面锁定）：碰撞危险首次形成时锁定局面与双方角色（HeadOn/Crossing/Overtaking；包括交叉之后因方位变化看起来像追越的情况也不改判），保持到「碰撞危险解除或驶过让清」；解除后再形成才重新判定。唯一例外：未互见→互见的切换时刻开新时间带，按互见重新判定一次后锁定。
   直航船阶段（R17(a)(i)/(a)(ii)/(b)）在本次锁定期内单调推进：一旦进入 (a)(ii) 介入阶段（或 (b)），不因本船操纵使 TCPA 回升而回退到 (a)(i)；直航船的一次连续操纵按整段评估，安全驶过以整个危险期结束（或驶过）时的结果判断，不在转向中途截段判“不安全”。D06 场景：交叉，让路船甲不行动，直航船乙在 t=225 s（TCPA≈175 s）右转 120°，危险约 240 s 解除，驶过 ≥0.5 nm → R17 的 EndTime>220 且非 NotApplicable 的核查不得有 NotSatisfied。
   「危险解除」判据：当前不再满足碰撞危险判据并且正在分离（已过 CPA / TCPA≤0 或 DCPA 已 ≥ 阈值），或已驶过让清。保持现有追越释放行为（追越直到驶过让清）。
2. D03：显式互见（标量 vesselsInSight=true 或互见序列该时刻为 true）时适用 R13–R17，与能见度无关；显式 false 走 R19。
3. D04：互见改为时间序列。请求追加可选参数显式传入互见序列（如新类型 `ColregInSightSample(SimTime time, bool inSight)` 列表，阶梯保持），原标量 vesselsInSight 作为全程常量兼容入口。都未给时逐时刻推导：能见度 ≥ RestrictedVisibilityNm → 互见；能见度不良时两船距离 ≤ 能见度 → 互见，否则未互见。互见切换时刻要成为精确切分点（像现有能见度切换时刻那样，距离推导的切换时刻可在相邻采样间线性插值或取首个满足的采样时刻）。验收用例：能见度恒 1 nm、两船从 4000 m 对驶 → 首带 RestrictedVisibility，距离 ≤1 nm 后出现 HeadOn 带。
4. D05：R19(d)(i)(ii) 仅在紧迫局面正在形成或存在碰撞危险时判定，否则 NotApplicable。
5. 默认阈值改论文口径（A5，全部可配，新参数追加）：
   - 碰撞危险：DCPA < 1.0 nm 且 0 < TCPA ≤ 720 s（collisionRiskDcpaNm 默认改 1.0；新增 collisionRiskTcpaSeconds=720）。
   - 紧迫局面：DCPA < 0.3 nm 且 0 < TCPA ≤ 360 s（新增 closeQuartersDcpaNm=0.3、closeQuartersTcpaSeconds=360）；输出阶段（见 9）。
   - 大幅转向默认 30°（substantialTurnDeg 默认改 30）；大幅变速默认初速的 30%（新增 substantialSpeedChangeFraction=0.3，|Δv| ≥ fraction×行动前航速）；现有 substantialSpeedChangeMps 参数保留，语义写清（例如默认 0=不启用绝对判据，>0 时作为附加绝对阈值），写进 Assumptions。
   - 转向在 60 s 滑窗内判定（新增 substantialTurnWindowSeconds=60）：只有某 60 s 窗口内同向航向变化 ≥ 阈值才算大幅转向；多次小幅转向不累计为大幅。
   - 安全航速不做硬判：RuleCheckStatus 追加 NeedsReview（需研判）。R6 与 R19(b) 输出 NeedsReview，Explanation/Evidence 附观测航速与能见度；safeSpeedMps 仅作可配置提示值（超过时在说明里写“超过提示值”），R6/R19(b) 不得给 Satisfied/NotSatisfied。
   - 其余现有阈值保留；所有阈值写进 Assumptions。
6. A3：他船相对方位正船首/正船尾（0°/180°）的交叉角色同时参考他船视角；两船视角矛盾时按存疑处理并标注（band.Doubt=true，Basis 写原因）。
7. A4：船首向互差 ≤ HeadOnHalfAngleDeg 且他船相对方位在船首 ±headOnDoubtBearingDeg（新增，默认 22.5）以内但超出 HeadOnForwardHalfAngleDeg（15°）→ 按对遇（R14(c)），标 Doubt。方位 30° 的反向船仍不是对遇。
8. D07/A6：ColregRuleId 追加 R5、R6、R7、R34_35（必须有以 "R34" 开头的名字）；ColregRules.Catalog 含 R5、R6、R7、R8、R9、R13–R17、R19、R34_35。无数据可判的 R5（瞭望）、R34_35（操纵与警告信号/声号）输出 RuleCheckStatus 追加值 NotAssessable，Explanation 列出所需证据（如 VDR 音频、驾驶台值班记录、雷达/ARPA 记录）；R6 输出 NeedsReview。R7 在存在碰撞危险的区段按 CPA 序列判（给出首次形成危险时刻、DCPA/TCPA 演变；本引擎就是基于航迹 CPA 序列，可判为 Satisfied=“可由 CPA 序列识别碰撞危险”的技术事实，或 Partial，并说明“是否实际使用雷达标绘需证据”；无数据则 NotAssessable）。R9：标狭水道且请求给出航道折线（新增可选请求参数，如航道中心线 EnuPosition 列表）时判本船是否在航道中线右侧（靠右），否则 NotAssessable；未标狭水道仍 NotApplicable。
   重要：验收 NoRisk_NoRolesAssigned 要求全程无碰撞危险时，除 R9 外所有核查项都是 NotApplicable。所以 R5/R6/R7/R34_35 只在存在碰撞危险（或能见度不良未互见且存在危险/紧迫局面正在形成）的区段输出 NotAssessable/NeedsReview/判定；无碰撞危险区段不输出或输出 NotApplicable。
9. D08/A7：
   - EncounterSituation 追加 NarrowChannel、ImmediateDanger、PostCollision、Undetermined。
   - ColregTimeBand 新增 `bool? InSight`、`string BandId`、`string GiveWayVesselId`/`StandOnVesselId`（无则 null）、`string Basis`、`bool Doubt`、`ColregDangerStage DangerStage`（新枚举：None, CollisionRisk, CloseQuarters, ImmediateDanger；ImmediateDanger 可定义为紧迫局面且 TCPA ≤ StandOnEmergencyTcpaSeconds，表示 R17(b)/R2(b) 紧迫危险）。
   - 不要因进入紧迫局面就把 band.Situation 改成 ImmediateDanger：验收很多用例在 DCPA=0、TCPA≤360 s 时仍要求首带 Situation 是 HeadOn/Crossing/Overtaking。band.Situation 保持锁定的会遇类型；阶段用 DangerStage 表达。是否因阶段变化切带由你权衡，但验收 TimeBands_ContiguousAndCoverOverlap 要求相邻带 (Situation,OwnRole,TargetRole) 不能完全相同，TimeBands_SplitWhenRiskEnds 要求序列恰为 [Crossing, NoCollisionRisk]，所以推荐：切带只由 Situation/角色/互见变化触发，DangerStage 记录该带内达到的最高阶段；另在报告里新增 `IReadOnlyList<ColregStageInterval> DangerStages`（起止时刻+阶段，确定性 ID）供适配层把 ImmediateDanger 区段映射为契约 situation=ImmediateDanger。在 EncounterSituation.ImmediateDanger 的 XML 注释里说明这一映射。
   - ColregRuleCheck 新增 `string CheckId`（确定性：由 caseId+规则+条款+船号+起止时刻派生，如 `{caseId}:{rule}:{clause}:{vesselId}:{startMs}-{endMs}`，禁止 GUID/随机/当前时间）、`ColregReviewStatus ReviewStatus`（新枚举 Draft, Confirmed, Rejected, Modified；引擎输出恒为 Draft）、`IReadOnlyList<string> EvidenceIds`（请求追加可选 evidenceIds，原样引用）、`double? AtTimeSec`。BandId 同法派生。请求追加可选 `caseId`（缺省 "case"）。
   - 同输入同输出（验收 Determinism 用完整指纹比较）。
10. 自测：`RestrictedVisibilityOrExplicitNotInSight_TakesPrecedence(1.9, true)` 把 D03 当预期，要改为：(vis 1.9, inSight true) → HeadOn 适用 R14；(vis 8, inSight false) → R19。其它因默认阈值变化（30°、30%、1 nm/12 min、R19(b) 需研判）失效的自测按裁定改期望或显式传入阈值，并在注释里写原因。

## 已知与裁定冲突的验收用例（不改验收测试；按裁定实现；最终报告说明）
- ActionAcceptanceTests.R8_SubstantialTurnThreshold(10.0,true)/(25.0,true)：默认阈值下期望 10° 即明显，与 A5「大幅转向默认 30°」冲突。
- ActionAcceptanceTests.R19b_SafeSpeedProxy_ConfigurableThreshold：期望 5 m/s 硬判，与 A5「安全航速不做硬判，只出需研判」冲突。
- RobustnessAcceptanceTests.Thresholds_RestrictedVisibility_Configurable 第二个断言：能见度 2.5 nm、阈值 3 nm、两船距 2.16 nm、未给互见 → 按 D04「缺省距离≤能见度即互见」应为 HeadOn，测试期望 RestrictedVisibility。
其余验收用例（含 8 个 KnownDefect）目标全部通过。

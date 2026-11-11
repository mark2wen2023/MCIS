已完成第 1 阶段：新增 **30 个测试方法，参数展开为 57 项**，全部使用合成虚构数据。未运行 `dotnet test`，实际红灯结果待外部验证。

新增文件：[ColregFixRegressionTests.cs](/workspace/maritime-sim-design/unity/Tests_W1_Colreg/ColregFixRegressionTests.cs)。

| 缺陷／裁定 | 新增测试名 |
|---|---|
| D01/A1 | `D01_CrossingRoles_RemainLockedDuringGiveWayTurn` |
| D01/A1 | `D01_StandOnTurn_DoesNotCreateOvertakingBeforeRiskClears` |
| D02/A1 | `D02_HeadOnStarboardTurn_KeepsBothActionRolesUntilRiskClears` |
| D06/A1 | `D06_StandOnIndependentAction_IsNotFragmentedIntoViolations` |
| D03 | `D03_ExplicitInSight_AppliesR14InPoorVisibility` |
| D04 | `D04_InSightSeries_SplitsExactlyAndOverridesScalar` |
| D04/A1 | `D04_BecomingInSight_ReclassifiesOnceThenLocks` |
| D04 | `D04_DistanceWithinVisibility_DerivesHeadOnIncludingEquality` |
| D05 | `D05_R19d_WithoutRiskOrCloseQuarters_IsNotApplicable` |
| A5：1 nm/12 min | `A5_DefaultRisk_UsesOneNmAndTwelveMinuteLimits` |
| A5：0.3 nm/6 min | `A5_CloseQuarters_UsesPointThreeNmAndSixMinuteLimits` |
| A5：30° | `A5_DefaultSubstantialTurn_RequiresThirtyDegrees` |
| A5：30% 变速 | `A5_DefaultSpeedChange_UsesThirtyPercentOfInitialSpeed` |
| A5：60 s 滑窗 | `A5_TurnWindow_DoesNotAccumulateSmallTurnsAcrossSixtySeconds` |
| A5：配置与假设回显 | `A5_NewThresholds_ChangeRiskStageAndActionAndAppearInAssumptions` |
| A5：R19(b) | `A5_R19b_IsNeedsReviewWithObservedSpeedAndVisibility` |
| A3：他船视角 | `A3_BowAxisCrossing_UsesOtherVesselPerspective` |
| A3：矛盾视角 | `A3_ConflictingCrossingPerspectives_MarksDoubtAndBasis` |
| A4：存疑对遇 | `A4_ReciprocalWithinDoubtSector_IsHeadOnWithDoubt` |
| A4：可配边界 | `A4_DoubtBearing_IsConfigurableAndExcludesThirtyDegreesByDefault` |
| D07/A6：目录 | `D07_Catalog_IncludesAllRequiredRules` |
| D07/A6：缺少证据 | `D07_LookoutAndSignals_AreNotAssessableWithRequiredEvidence` |
| A5/D07：R6 | `A5_D07_R6_IsNeedsReviewWithObservedSpeedAndVisibility` |
| D07：R7 CPA 序列 | `D07_R7_UsesCpaSequenceAtFirstRiskTime` |
| D07：R9 缺少几何 | `D07_R9_NarrowWithoutCenterline_IsNotAssessable` |
| D07：R9 航道折线 | `D07_R9_ChannelPolyline_JudgesRightSideAlongLocalTravelDirection` |
| D08：互见与角色字段 | `D08_Bands_ExposeInSightRolesAndBasis` |
| D08/A7：确定性 ID | `D08_Ids_AreNonEmptyUniqueStableAndCaseScoped` |
| D08/A7：草稿与证据引用 | `D08_Checks_AreDraftAndPreserveEvidenceIdsVerbatim` |
| D08：危险阶段 | `D08_DangerStages_ProgressWithoutSplittingLockedSituation` |

已修改 [ColregEngineTests.cs](/workspace/maritime-sim-design/unity/Tests_W1_Colreg/ColregEngineTests.cs:90)：`(1.9,true)` 期望改为 HeadOn/R14，`(8,false)` 保持 R19。

最小 API 骨架位于 [ColregModels.cs](/workspace/maritime-sim-design/unity/Assets/_Project/Scripts/Domain/Colreg/ColregModels.cs) 和 [ColregThresholds.cs](/workspace/maritime-sim-design/unity/Assets/_Project/Scripts/Domain/Colreg/ColregThresholds.cs)：

- 追加局面、规则和核查状态枚举值；新增 `ColregDangerStage`、`ColregReviewStatus`。
- 新增 `ColregInSightSample`、`ColregStageInterval`；请求末尾追加互见序列、航道中心线、案件号、证据 ID 参数。
- 时间带、核查项和报告追加规定的元数据属性；输出保持 null/default，`DangerStages` 暂为空集合。
- 追加六个阈值参数及属性：危险 TCPA、紧迫 DCPA/TCPA、变速比例、转向滑窗、对遇存疑方位。

现有判定逻辑及原默认阈值未改；只读验收、缺陷单和规格文件哈希校验一致。

执行指定 **`dotnet build` 成功：0 警告、0 错误**。
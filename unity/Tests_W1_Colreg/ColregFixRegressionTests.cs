using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Colreg;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Models;
using Xunit;

namespace Mcis.Tests.W1
{
    /// <summary>
    /// W1 返修回归：以 logs/w1-fix-spec.md 第 1–9 项及架构师裁定为预期。
    /// 全部案件、船名、证据标识和航迹均为合成虚构数据；阶段一的行为检查持续约束阶段二实现。
    /// </summary>
    public sealed class ColregFixRegressionTests
    {
        private const string Own = "返修虚构甲船";
        private const string Target = "返修虚构乙船";
        private const double MetersPerNm = 1852.0;

        // 规格 1：D01/D02/D06，局面、角色锁定与 R17 单次连续行动。
        [Fact]
        public void D01_CrossingRoles_RemainLockedDuringGiveWayTurn()
        {
            var report = Analyze(new SyntheticShip(0, 0, 0, 5).Order(250, 60).Run(450), CrossingTarget().Run(450));
            Assert.Equal(EncounterSituation.Crossing, report.TimeBands.First().Situation);
            var active = report.TimeBands.Where(b => b.Situation != EncounterSituation.NoCollisionRisk).ToArray();
            Assert.NotEmpty(active);
            Assert.All(active, b =>
            {
                Assert.Equal(EncounterSituation.Crossing, b.Situation);
                Assert.Equal(TrafficRole.GiveWay, b.OwnRole);
                Assert.Equal(TrafficRole.StandOn, b.TargetRole);
            });
            Assert.Equal(EncounterSituation.NoCollisionRisk, report.TimeBands.Last().Situation);
            Assert.DoesNotContain(Checks(report, ColregRuleId.R16, Target), c => c.Status == RuleCheckStatus.NotSatisfied);
        }

        [Fact]
        public void D01_StandOnTurn_DoesNotCreateOvertakingBeforeRiskClears()
        {
            var report = Analyze(new SyntheticShip(0, 0, 0, 5).Run(450), CrossingTarget().Order(250, 330).Run(450));
            Assert.Equal(TrafficRole.StandOn, report.TimeBands.First().TargetRole);
            var active = report.TimeBands.Where(b => b.Situation != EncounterSituation.NoCollisionRisk).ToArray();
            Assert.NotEmpty(active);
            Assert.All(active, b =>
            {
                Assert.Equal(EncounterSituation.Crossing, b.Situation);
                Assert.Equal(TrafficRole.GiveWay, b.OwnRole);
                Assert.Equal(TrafficRole.StandOn, b.TargetRole);
            });
        }

        [Fact]
        public void D02_HeadOnStarboardTurn_KeepsBothActionRolesUntilRiskClears()
        {
            var report = Analyze(new SyntheticShip(0, 0, 0, 5).Order(100, 30).Run(450), new SyntheticShip(0, 4000, 180, 5).Run(450));
            var active = report.TimeBands.Where(b => b.Situation != EncounterSituation.NoCollisionRisk).ToArray();
            Assert.NotEmpty(active);
            Assert.All(active, b =>
            {
                Assert.Equal(EncounterSituation.HeadOn, b.Situation);
                Assert.Equal(TrafficRole.BothActionRequired, b.OwnRole);
                Assert.Equal(TrafficRole.BothActionRequired, b.TargetRole);
            });
            Assert.DoesNotContain(Checks(report, ColregRuleId.R16, Target), c => c.Status == RuleCheckStatus.NotSatisfied);
        }

        [Fact]
        public void A1_A5_EarlySixtyDegreeTurn_RemainsCrossingUntilNewRiskThresholdClears()
        {
            // A1/A5：60 s 右转 60° 后 DCPA 约 0.638 nm，仍小于新默认 1 nm，须锁定至约 280 s。
            // 验收 TimeBands_SplitWhenRiskEnds 沿用旧 0.5 nm 的 60–80 s 释放断言，与裁定冲突。
            var report = Analyze(new SyntheticShip(0, 0, 0, 5).Order(60, 60).Run(450), CrossingTarget().Run(450));
            Assert.Equal(new[] { EncounterSituation.Crossing, EncounterSituation.NoCollisionRisk },
                report.TimeBands.Select(b => b.Situation).ToArray());
            Assert.Equal(EncounterSituation.Crossing, BandAt(report, 70).Situation);
            Assert.InRange(report.TimeBands.First().EndTime.Seconds, 270, 290);
            Assert.Equal(TrafficRole.GiveWay, report.TimeBands.First().OwnRole);
        }

        [Fact]
        public void D06_StandOnIndependentAction_IsNotFragmentedIntoViolations()
        {
            // 与裁定场景同样：6°/s 连续右转，225 s 发令，TCPA 约 175 s。
            var report = Analyze(new SyntheticShip(0, 0, 0, 5).Run(450), CrossingTarget().Order(225, 30).Run(450));
            Assert.Equal(TrafficRole.StandOn, report.TimeBands.First().TargetRole);
            var during = Checks(report, ColregRuleId.R17, Target)
                .Where(c => c.EndTime.Seconds > 220 && c.Status != RuleCheckStatus.NotApplicable).ToArray();
            Assert.NotEmpty(during);
            Assert.DoesNotContain(during, c => c.Status == RuleCheckStatus.NotSatisfied);
            Assert.Contains(during, c => c.Clause == "R17(a)(ii)" && c.ActualAction.Turn == TurnDirection.Starboard);
            // 进入介入后，危险期内不因自己的行动使 TCPA 回升而回退到保向阶段。
            var intervention = during.Where(c => c.Clause == "R17(a)(ii)").Min(c => c.StartTime.Seconds);
            double riskEnd = report.TimeBands.First(b => b.Situation == EncounterSituation.Crossing).EndTime.Seconds;
            Assert.DoesNotContain(during, c => c.Clause == "R17(a)(i)" && c.StartTime.Seconds >= intervention && c.StartTime.Seconds < riskEnd);
        }

        // 规格 2：D03，显式互见与能见度无关。
        [Fact]
        public void D03_ExplicitInSight_AppliesR14InPoorVisibility()
        {
            var report = Analyze(Linear(0, 0, 0, 5, 100), Linear(0, 1500, 180, 5, 100), visibility: 1, inSight: true);
            var band = report.TimeBands.First();
            Assert.Equal(EncounterSituation.HeadOn, band.Situation);
            Assert.Contains(ColregRuleId.R14, band.ApplicableRules);
            Assert.DoesNotContain(ColregRuleId.R19, band.ApplicableRules);
            Assert.Contains(Checks(report, ColregRuleId.R14, Own), c => c.Status != RuleCheckStatus.NotApplicable);
        }

        // 规格 3：D04，显式阶梯序列的非网格时刻、双向转换与距离推导。
        [Fact]
        public void D04_InSightSeries_SplitsExactlyAndOverridesScalar()
        {
            var sight = new[] { Sight(0, false), Sight(103, true), Sight(181, false), Sight(237, true) };
            var report = Analyze(Linear(0, 0, 0, 5, 300), Linear(0, 4000, 180, 5, 300),
                visibility: 1, inSight: false, sight: sight);
            Assert.Equal(new[] { EncounterSituation.RestrictedVisibility, EncounterSituation.HeadOn,
                EncounterSituation.RestrictedVisibility, EncounterSituation.HeadOn }, report.TimeBands.Select(b => b.Situation).ToArray());
            Assert.Equal(new[] { 0.0, 103.0, 181.0, 237.0 }, report.TimeBands.Select(b => b.StartTime.Seconds).ToArray());
            Assert.Equal(new[] { 103.0, 181.0, 237.0, 300.0 }, report.TimeBands.Select(b => b.EndTime.Seconds).ToArray());
            Assert.Equal(new bool?[] { false, true, false, true }, report.TimeBands.Select(b => b.InSight).ToArray());
            Assert.Equal(EncounterSituation.HeadOn, BandAt(report, 103).Situation);
        }

        [Fact]
        public void D04_D08_InSightTransitionAtFinalTime_KeepsZeroLengthBandAndUniqueCheckIds()
        {
            // 转换端点归后一带，即使转换恰在观测终点也保留新带；不得重复生成同区间 R8 核查 ID。
            var report = Analyze(Linear(0, 0, 0, 5, 100), Linear(0, 4000, 180, 5, 100),
                visibility: 1, inSight: null, sight: new[] { Sight(0, false), Sight(100, true) },
                caseId: "虚构案件-末时刻互见");
            Assert.Equal(new[] { EncounterSituation.RestrictedVisibility, EncounterSituation.HeadOn },
                report.TimeBands.Select(b => b.Situation).ToArray());
            Assert.Equal(100, report.TimeBands.Last().StartTime.Seconds);
            Assert.Equal(100, report.TimeBands.Last().EndTime.Seconds);
            Assert.Equal(true, report.TimeBands.Last().InSight);
            AssertIds(report.RuleChecks.Select(c => c.CheckId));
            Assert.Contains(Checks(report, ColregRuleId.R14, Own), c => c.StartTime.Seconds == 100 &&
                c.EndTime.Seconds == 100 && c.Status == RuleCheckStatus.Partial);
        }

        [Fact]
        public void D04_BecomingInSight_ReclassifiesOnceThenLocks()
        {
            var own = new SyntheticShip(0, 0, 0, 5).Order(60, 30).Order(140, 60).Run(300);
            var report = Analyze(own, new SyntheticShip(0, 4000, 180, 5).Run(300), visibility: 1, inSight: null,
                sight: new[] { Sight(0, false), Sight(103, true) });
            Assert.Equal(EncounterSituation.RestrictedVisibility, report.TimeBands.First().Situation);
            // W1.1 D12 复测裁定：103s互见时仍在转向历史窗口中，先延后。
            // 第一阶段写成130s稳定才锁定，遗漏了“风险形成后120s”上限。
            // 风险自0s一直存在；互见重判不重置风险起点，故120s须强制锁定并标存疑。
            var pending = BandAt(report, 103);
            Assert.Equal(103, pending.StartTime.Seconds, 6);
            Assert.Equal(EncounterSituation.Undetermined, pending.Situation);
            Assert.Equal(ColregDoubtReasons.PendingStableHeading, pending.DoubtReason);
            Assert.Equal(120, pending.EndTime.Seconds, 6);
            var visible = BandAt(report, 120);
            Assert.Equal(EncounterSituation.Crossing, visible.Situation);
            Assert.True(visible.Doubt);
            Assert.Equal(ColregDoubtReasons.LockedDuringTurn, visible.DoubtReason);
            var locked = report.TimeBands.Where(b => b.StartTime.Seconds >= 120 && b.Situation != EncounterSituation.NoCollisionRisk).ToArray();
            Assert.NotEmpty(locked);
            Assert.All(locked, b =>
            {
                Assert.Equal(EncounterSituation.Crossing, b.Situation);
                Assert.True(b.Doubt);
                Assert.Equal(ColregDoubtReasons.LockedDuringTurn, b.DoubtReason);
                Assert.Equal(visible.OwnRole, b.OwnRole);
                Assert.Equal(visible.TargetRole, b.TargetRole);
            });
        }

        [Fact]
        public void D04_DistanceWithinVisibility_DerivesHeadOnIncludingEquality()
        {
            var environment = new[] { Environment(0, 1) };
            var report = Analyze(Linear(0, 0, 0, 5, 380), Linear(0, 4000, 180, 5, 380),
                visibility: null, inSight: null, environment: environment);
            Assert.Equal(EncounterSituation.RestrictedVisibility, report.TimeBands.First().Situation);
            Assert.Equal(false, report.TimeBands.First().InSight);
            var visible = report.TimeBands.FirstOrDefault(b => b.Situation == EncounterSituation.HeadOn);
            Assert.NotNull(visible);
            // 距离 4000-10t = 1852；允许插值切分或首个满足条件的 10 s 网格点。
            Assert.InRange(visible.StartTime.Seconds, 214.8 - 1e-6, 220.0);
            Assert.Equal(true, visible.InSight);
            var equality = Analyze(Linear(0, 0, 0, 5, 10), Linear(0, MetersPerNm, 180, 5, 10), visibility: 1, inSight: null);
            Assert.Equal(EncounterSituation.HeadOn, equality.TimeBands.First().Situation);
            Assert.Equal(true, equality.TimeBands.First().InSight);
        }

        // 规格 4：D05，前方与正横后方都不能脱离危险前提判 R19(d) 违反。
        [Theory]
        [InlineData(4000.0, 4000.0, 180.0, 340.0)]
        [InlineData(4000.0, -4000.0, 0.0, 20.0)]
        public void D05_R19d_WithoutRiskOrCloseQuarters_IsNotApplicable(double east, double north, double heading, double turnTo)
        {
            var own = new SyntheticShip(0, 0, 0, 5).Order(30, turnTo).Run(200);
            var target = new SyntheticShip(east, north, heading, 5).Run(200);
            // 检查合成数据本身：全程 DCPA 至少 1 nm，不存在新默认口径的危险。
            for (int i = 0; i < own.Length; i++)
                Assert.True(CpaCalculator.CalculateFromSamples(own[i], target[i]).DcpaNm >= 1);
            var report = Analyze(own, target, visibility: 0.5, inSight: false);
            var checks = Checks(report, ColregRuleId.R19, Own).Where(c => c.Clause.StartsWith("R19(d)", StringComparison.Ordinal)).ToArray();
            Assert.NotEmpty(checks);
            Assert.Contains(checks, c => c.Clause == "R19(d)(i)");
            Assert.Contains(checks, c => c.Clause == "R19(d)(ii)");
            Assert.All(checks, c => Assert.Equal(RuleCheckStatus.NotApplicable, c.Status));
        }

        // 规格 5：A5，用行为测试约束新默认值和严格/闭边界，不先修改生产默认值。
        [Theory]
        [InlineData(0.75, 600.0, true)]
        [InlineData(0.999, 720.0, true)]
        [InlineData(1.0, 600.0, false)]
        [InlineData(0.2, 721.0, false)]
        [InlineData(0.2, 720.0, true)]
        [InlineData(0.2, 0.0, false)]
        public void A5_DefaultRisk_UsesOneNmAndTwelveMinuteLimits(double dcpaNm, double tcpa, bool risk)
        {
            var report = Reciprocal(dcpaNm, tcpa);
            Assert.Equal(risk, report.TimeBands.First().Situation != EncounterSituation.NoCollisionRisk);
            if (!risk)
            {
                Assert.Equal(TrafficRole.None, report.TimeBands.First().OwnRole);
                Assert.Equal(TrafficRole.None, report.TimeBands.First().TargetRole);
            }
        }

        [Theory]
        [InlineData(0.299, 360.0, ColregDangerStage.CloseQuarters)]
        [InlineData(0.3, 360.0, ColregDangerStage.CollisionRisk)]
        [InlineData(0.299, 361.0, ColregDangerStage.CollisionRisk)]
        [InlineData(0.299, 60.0, ColregDangerStage.ImmediateDanger)]
        [InlineData(0.299, 61.0, ColregDangerStage.CloseQuarters)]
        [InlineData(1.1, 360.0, ColregDangerStage.None)]
        public void A5_CloseQuarters_UsesPointThreeNmAndSixMinuteLimits(double dcpaNm, double tcpa, ColregDangerStage stage)
        {
            // 0.1 s 观测窗不会跨过这些整数秒边界；阶段仍由输出行为判定。
            var report = Reciprocal(dcpaNm, tcpa);
            Assert.Equal(stage, report.TimeBands.First().DangerStage);
            if (stage != ColregDangerStage.None)
                Assert.NotEqual(EncounterSituation.ImmediateDanger, report.TimeBands.First().Situation);
        }

        [Theory]
        [InlineData(29.0, false)]
        [InlineData(30.0, true)]
        public void A5_DefaultSubstantialTurn_RequiresThirtyDegrees(double turn, bool substantial)
        {
            var own = new SyntheticShip(0, 0, 0, 5).Order(10, turn).Run(80);
            AssertSubstantial(Analyze(own, CrossingTarget().Run(80), visibility: 0.5, inSight: false), substantial);
        }

        [Theory]
        [InlineData(5.0, 1.0, false)]
        [InlineData(5.0, 1.5, true)]
        [InlineData(10.0, 2.0, false)]
        [InlineData(10.0, 3.0, true)]
        [InlineData(2.0, 0.6, true)]
        [InlineData(2.0, 0.5, false)]
        public void A5_DefaultSpeedChange_UsesThirtyPercentOfInitialSpeed(double initialSpeed, double reduction, bool substantial)
        {
            var own = new SyntheticShip(0, 0, 0, initialSpeed).Order(10, 0, initialSpeed - reduction).Run(80);
            var target = new SyntheticShip(initialSpeed * 400, initialSpeed * 400, 270, initialSpeed).Run(80);
            AssertSubstantial(Analyze(own, target, visibility: 0.5, inSight: false), substantial);
        }

        [Fact]
        public void A5_TurnWindow_DoesNotAccumulateSmallTurnsAcrossSixtySeconds()
        {
            // 显式 30° 隔离旧默认 10° 的影响；每 70 s 才右转 10°，全程净转 40°。
            var own = new SyntheticShip(0, 0, 0, 2).Order(10, 10).Order(80, 20).Order(150, 30).Order(220, 40).Run(260);
            var target = new SyntheticShip(0, 2400, 180, 2).Run(260);
            var report = Analyze(own, target, new ColregThresholds(substantialTurnDeg: 30), visibility: 0.5, inSight: false);
            AssertSubstantial(report, false);
            // 正对照：同样总转幅在一次连续操纵中完成，必须识别；滑窗本身也可配置。
            var burst = new SyntheticShip(0, 0, 0, 2).Order(10, 40).Run(260);
            AssertSubstantial(Analyze(burst, target, new ColregThresholds(substantialTurnDeg: 30), visibility: 0.5, inSight: false), true);
            AssertSubstantial(Analyze(own, target, new ColregThresholds(substantialTurnDeg: 30, substantialTurnWindowSeconds: 300),
                visibility: 0.5, inSight: false), true);
        }

        [Fact]
        public void A5_TurnWindow_FirstActionTimeAccountsForMovingWindowStart()
        {
            // 保留源点即可观察阈值插值：H35=7°，H95=37°，首次在 60 s 窗口内转够 30° 是 95 s。
            // 窗口左端也在移动，不能把 t=100 的左端航向固定后只对窗口右端作比例插值。
            var own = new[] { Sample(0, 0, 0, 0, 5), Sample(50, 0, 250, 10, 5), Sample(100, 0, 500, 40, 5) };
            var report = Analyze(own, Linear(0, 5000, 180, 5, 100),
                new ColregThresholds(sampleIntervalSeconds: 100), visibility: 0.5, inSight: false);
            var check = Checks(report, ColregRuleId.R8, Own).First(c => c.Status != RuleCheckStatus.NotApplicable);
            Assert.True(check.ActualAction.FirstSubstantialActionTime.HasValue);
            Assert.Equal(95, check.ActualAction.FirstSubstantialActionTime.Value.Seconds, 6);
        }

        [Fact]
        public void A5_FirstActionTime_UsesEarlierSpeedTriggerWithinTurningSegment()
        {
            // 同一观测段：40° 转向的 30° 门限在 7.5 s，5→2 m/s 的 30% 变速门限在 5 s。
            // 首次行动时刻必须取两种判据的较早值，不能由先检查转向就盖掉更早的变速。
            var own = new[] { Sample(0, 0, 0, 0, 5), Sample(10, 0, 50, 40, 2) };
            var report = Analyze(own, Linear(0, 4000, 180, 5, 10), visibility: 0.5, inSight: false);
            var check = Checks(report, ColregRuleId.R8, Own).First(c => c.Status != RuleCheckStatus.NotApplicable);
            Assert.True(check.ActualAction.FirstSubstantialActionTime.HasValue);
            Assert.Equal(5, check.ActualAction.FirstSubstantialActionTime.Value.Seconds, 6);
        }

        [Fact]
        public void A5_NewThresholds_ChangeRiskStageAndActionAndAppearInAssumptions()
        {
            var horizon = new ColregThresholds(collisionRiskTcpaSeconds: 123);
            Assert.Equal(EncounterSituation.NoCollisionRisk, Reciprocal(0.2, 150, horizon).TimeBands.First().Situation);
            Assert.NotEqual(EncounterSituation.NoCollisionRisk, Reciprocal(0.2, 150).TimeBands.First().Situation);
            var close = new ColregThresholds(closeQuartersDcpaNm: 0.41, closeQuartersTcpaSeconds: 456);
            var report = Reciprocal(0.35, 400, close);
            Assert.Equal(ColregDangerStage.CloseQuarters, report.TimeBands.First().DangerStage);
            var own = new SyntheticShip(0, 0, 0, 5).Order(10, 0, 4).Run(80);
            var fractional = new ColregThresholds(substantialSpeedChangeFraction: 0.15);
            AssertSubstantial(Analyze(own, CrossingTarget().Run(80), fractional, visibility: 0.5, inSight: false), true);
            // 不约束说明句式，只核查配置值确实进入可审计假设。
            Assert.Contains(Reciprocal(0.2, 100, horizon).Assumptions, a => a.Contains("123"));
            Assert.Contains(report.Assumptions, a => a.Contains("0.41"));
            Assert.Contains(report.Assumptions, a => a.Contains("456"));
            var fractionReport = Analyze(own, CrossingTarget().Run(80), fractional, visibility: 0.5, inSight: false);
            Assert.Contains(fractionReport.Assumptions, a => a.Contains("0.15") || a.Contains("15%"));
        }

        [Theory]
        [InlineData(4.0, 5.0)]
        [InlineData(7.0, 5.0)]
        [InlineData(7.0, 8.0)]
        public void A5_R19b_IsNeedsReviewWithObservedSpeedAndVisibility(double speed, double hint)
        {
            var report = SpeedReviewReport(speed, hint, false);
            var checks = Checks(report, ColregRuleId.R19, Own).Where(c => c.Clause == "R19(b)").ToArray();
            AssertReviewEvidence(checks, speed, 0.5);
            if (speed > hint) Assert.Contains(checks, c => c.Explanation.Contains("超过提示值"));
        }

        // 规格 6：A3，正船首同时参考他船视角；正船尾先适用 R13，不伪造交叉场景。
        [Fact]
        public void A3_BowAxisCrossing_UsesOtherVesselPerspective()
        {
            // 甲看乙在正船首；乙向西慢行，看甲在左舷 270°；TCPA≈96 s、DCPA≈98 m。
            var report = Analyze(Linear(0, 0, 0, 5, 5), Linear(0, 500, 270, 1, 5));
            var band = report.TimeBands.First();
            Assert.Equal(EncounterSituation.Crossing, band.Situation);
            Assert.Equal(TrafficRole.GiveWay, band.OwnRole);
            Assert.Equal(TrafficRole.StandOn, band.TargetRole);
        }

        [Fact]
        public void A3_ConflictingCrossingPerspectives_MarksDoubtAndBasis()
        {
            // 双方都看对方在右舷 45°，又在对遇存疑扇区之外。
            var report = Analyze(Linear(0, 0, 0, 5, 5), Linear(500, 500, 180, 5, 5));
            var band = report.TimeBands.First();
            Assert.Equal(EncounterSituation.Crossing, band.Situation);
            Assert.True(band.Doubt);
            Assert.False(string.IsNullOrWhiteSpace(band.Basis));
        }

        // 规格 7：A4，R14(c) 扩展到 ±22.5°，并显式标存疑。
        [Theory]
        [InlineData(-22.5)]
        [InlineData(-20.0)]
        [InlineData(20.0)]
        [InlineData(22.5)]
        public void A4_ReciprocalWithinDoubtSector_IsHeadOnWithDoubt(double bearing)
        {
            var band = OffBow(bearing).TimeBands.First();
            Assert.Equal(EncounterSituation.HeadOn, band.Situation);
            Assert.Equal(TrafficRole.BothActionRequired, band.OwnRole);
            Assert.Equal(TrafficRole.BothActionRequired, band.TargetRole);
            Assert.True(band.Doubt);
            Assert.False(string.IsNullOrWhiteSpace(band.Basis));
            Assert.Contains(ColregRuleId.R14, band.ApplicableRules);
        }

        [Theory]
        [InlineData(22.5, 174.0)]
        [InlineData(-22.5, 186.0)]
        public void A4_DoubtSector_UsesOwnViewEvenWhenOtherViewIsOutsideSector(double bearing, double targetHeading)
        {
            // A4 按本船看他船的船首 ±22.5° 存疑扇区；航向偏差 6° 会使他船视角达到 ±28.5°。
            // 不能额外要求他船视角也在 ±22.5° 内而缩小裁定规定的存疑范围。
            var report = Analyze(Linear(0, 0, 0, 5, 1),
                Linear(1400 * Sin(bearing), 1400 * Cos(bearing), targetHeading, 5, 1));
            var band = Assert.Single(report.TimeBands);
            Assert.Equal(EncounterSituation.HeadOn, band.Situation);
            Assert.Equal(TrafficRole.BothActionRequired, band.OwnRole);
            Assert.Equal(TrafficRole.BothActionRequired, band.TargetRole);
            Assert.True(band.Doubt);
            Assert.False(string.IsNullOrWhiteSpace(band.Basis));
        }

        [Fact]
        public void A4_DoubtBearing_IsConfigurableAndExcludesThirtyDegreesByDefault()
        {
            Assert.Equal(EncounterSituation.Crossing, OffBow(30).TimeBands.First().Situation);
            Assert.Equal(EncounterSituation.Crossing, OffBow(20, new ColregThresholds(headOnDoubtBearingDeg: 19)).TimeBands.First().Situation);
            var expanded = OffBow(24, new ColregThresholds(headOnDoubtBearingDeg: 25)).TimeBands.First();
            Assert.Equal(EncounterSituation.HeadOn, expanded.Situation);
            Assert.True(expanded.Doubt);
        }

        // 规格 8：D07/A6，实际目录、资料不足状态、CPA 技术事实及 R9 折线几何。
        [Fact]
        public void D07_Catalog_IncludesAllRequiredRules()
        {
            foreach (var id in new[] { ColregRuleId.R5, ColregRuleId.R6, ColregRuleId.R7, ColregRuleId.R8, ColregRuleId.R9,
                ColregRuleId.R13, ColregRuleId.R14, ColregRuleId.R15, ColregRuleId.R16, ColregRuleId.R17, ColregRuleId.R19, ColregRuleId.R34_35 })
            {
                Assert.Contains(ColregRules.Catalog, d => d.Id == id);
                var definition = ColregRules.Get(id);
                Assert.NotNull(definition);
                Assert.False(string.IsNullOrWhiteSpace(definition.Summary));
            }
        }

        [Fact]
        public void D07_LookoutAndSignals_AreNotAssessableWithRequiredEvidence()
        {
            var report = Reciprocal(0, 300);
            foreach (var rule in new[] { ColregRuleId.R5, ColregRuleId.R34_35 })
            {
                var checks = Checks(report, rule, Own).ToArray();
                Assert.NotEmpty(checks);
                Assert.All(checks, c =>
                {
                    Assert.Equal(RuleCheckStatus.NotAssessable, c.Status);
                    Assert.True(new[] { "VDR", "音频", "值班", "记录" }.Any(c.Explanation.Contains), c.Explanation);
                });
            }
            // 兼容裁定对 NoRisk_NoRolesAssigned 的限制，缺证据项不能在无危险时假造适用结论。
            var noRisk = Reciprocal(2, 300);
            Assert.All(noRisk.RuleChecks.Where(c => c.RuleId != ColregRuleId.R9), c => Assert.Equal(RuleCheckStatus.NotApplicable, c.Status));
        }

        [Theory]
        [InlineData(4.0, 5.0)]
        [InlineData(7.0, 5.0)]
        [InlineData(7.0, 8.0)]
        public void A5_D07_R6_IsNeedsReviewWithObservedSpeedAndVisibility(double speed, double hint)
        {
            var report = SpeedReviewReport(speed, hint, true);
            var checks = Checks(report, ColregRuleId.R6, Own).ToArray();
            AssertReviewEvidence(checks, speed, 8);
            if (speed > hint) Assert.Contains(checks, c => c.Explanation.Contains("超过提示值"));
        }

        [Fact]
        public void D07_R7_UsesCpaSequenceAtFirstRiskTime()
        {
            var report = Analyze(Linear(0, 0, 0, 5, 100), Linear(0.25 * MetersPerNm, 7500, 180, 5, 100));
            var checks = Checks(report, ColregRuleId.R7, Own).Where(c => c.Status != RuleCheckStatus.NotApplicable).ToArray();
            Assert.NotEmpty(checks);
            var first = checks.First();
            Assert.Equal(30, first.StartTime.Seconds, 6); // TCPA 首次进入 720 s。
            Assert.True(first.Status == RuleCheckStatus.Satisfied || first.Status == RuleCheckStatus.Partial);
            Assert.Equal(0.25 * MetersPerNm, first.Evidence.DcpaM, 6);
            Assert.Equal(720, first.Evidence.TcpaSeconds, 6);
            Assert.Equal(650, checks.Last().Evidence.EndTcpaSeconds, 6);
            Assert.Contains(checks, c => c.Explanation.Contains("雷达") || c.Explanation.Contains("ARPA"));
        }

        [Fact]
        public void D07_R9_NarrowWithoutCenterline_IsNotAssessable()
        {
            var report = Analyze(Linear(0, 0, 0, 5, 10), Linear(0, 4000, 180, 5, 10), narrow: true);
            var checks = Checks(report, ColregRuleId.R9, Own).ToArray();
            Assert.NotEmpty(checks);
            Assert.All(checks, c =>
            {
                Assert.Equal(RuleCheckStatus.NotAssessable, c.Status);
                Assert.False(string.IsNullOrWhiteSpace(c.Explanation));
            });
            var unmarked = Analyze(Linear(0, 0, 0, 5, 10), Linear(0, 4000, 180, 5, 10));
            var notApplicable = Checks(unmarked, ColregRuleId.R9, Own).ToArray();
            Assert.NotEmpty(notApplicable);
            Assert.All(notApplicable, c => Assert.Equal(RuleCheckStatus.NotApplicable, c.Status));
        }

        [Theory]
        [InlineData(100.0, 0.0, 0.0, RuleCheckStatus.Satisfied)]
        [InlineData(-100.0, 0.0, 0.0, RuleCheckStatus.NotSatisfied)]
        [InlineData(1000.0, 900.0, 90.0, RuleCheckStatus.Satisfied)]
        [InlineData(1000.0, 1100.0, 90.0, RuleCheckStatus.NotSatisfied)]
        public void D07_R9_ChannelPolyline_JudgesRightSideAlongLocalTravelDirection(double east, double north, double heading, RuleCheckStatus expected)
        {
            // 折线先北后东；同样的“右侧”分别是东侧和南侧，不能硬编码为 ENU 东侧。
            var channel = new[] { new EnuPosition(0, -1000), new EnuPosition(0, 1000), new EnuPosition(2000, 1000) };
            var report = Analyze(Linear(east, north, heading, 5, 10), Linear(east + 4000, north + 4000, heading, 5, 10),
                narrow: true, channel: channel);
            var checks = Checks(report, ColregRuleId.R9, Own).ToArray();
            Assert.NotEmpty(checks);
            Assert.All(checks, c => Assert.Equal(expected, c.Status));
        }

        // 规格 9：D08/A7，校验实际输出，不能只用反射确认属性存在。
        [Fact]
        public void D08_Bands_ExposeInSightRolesAndBasis()
        {
            var crossing = Analyze(Linear(0, 0, 0, 5, 100), CrossingTarget().Run(100)).TimeBands.First();
            Assert.Equal(true, crossing.InSight);
            Assert.Equal(Own, crossing.GiveWayVesselId);
            Assert.Equal(Target, crossing.StandOnVesselId);
            Assert.False(string.IsNullOrWhiteSpace(crossing.Basis));
            var restricted = Analyze(Linear(0, 0, 0, 5, 100), CrossingTarget().Run(100), visibility: 1, inSight: false).TimeBands.First();
            Assert.Equal(false, restricted.InSight);
            Assert.Null(restricted.GiveWayVesselId);
            Assert.Null(restricted.StandOnVesselId);
            var noRisk = Reciprocal(2, 300).TimeBands.First();
            Assert.Null(noRisk.GiveWayVesselId);
            Assert.Null(noRisk.StandOnVesselId);
        }

        [Fact]
        public void D08_Ids_AreNonEmptyUniqueStableAndCaseScoped()
        {
            var own = Linear(0, 0, 0, 5, 450);
            var target = Linear(0, 4000, 180, 5, 450);
            var a = Analyze(own, target, caseId: "虚构案件-A");
            var repeat = Analyze(own.ToArray(), target.ToArray(), caseId: "虚构案件-A");
            var otherCase = Analyze(own, target, caseId: "虚构案件-B");
            var shorter = Analyze(Linear(0, 0, 0, 5, 449), Linear(0, 4000, 180, 5, 449), caseId: "虚构案件-A");
            Assert.True(a.TimeBands.Count >= 2);
            AssertIds(a.TimeBands.Select(b => b.BandId));
            AssertIds(a.RuleChecks.Select(c => c.CheckId));
            AssertIds(a.DangerStages.Select(s => s.StageId));
            AssertIds(otherCase.TimeBands.Select(b => b.BandId));
            AssertIds(otherCase.RuleChecks.Select(c => c.CheckId));
            AssertIds(otherCase.DangerStages.Select(s => s.StageId));
            Assert.Equal(MetadataFingerprint(a), MetadataFingerprint(repeat));
            Assert.Empty(a.TimeBands.Select(b => b.BandId).Intersect(otherCase.TimeBands.Select(b => b.BandId)));
            Assert.Empty(a.RuleChecks.Select(c => c.CheckId).Intersect(otherCase.RuleChecks.Select(c => c.CheckId)));
            Assert.Empty(a.DangerStages.Select(s => s.StageId).Intersect(otherCase.DangerStages.Select(s => s.StageId)));
            // 相同案件、相同起止时刻保留 ID；改变末带终点必须改变该带及对应核查 ID。
            Assert.Equal(a.TimeBands.First().BandId, shorter.TimeBands.First().BandId);
            Assert.NotEqual(a.TimeBands.Last().BandId, shorter.TimeBands.Last().BandId);
            var lastCheck = a.RuleChecks.First(c => c.StartTime.Seconds == 400 && c.EndTime.Seconds == 450);
            var shortenedCheck = shorter.RuleChecks.Single(c => c.RuleId == lastCheck.RuleId && c.Clause == lastCheck.Clause &&
                c.VesselId == lastCheck.VesselId && c.StartTime.Seconds == 400 && c.EndTime.Seconds == 449);
            Assert.NotEqual(lastCheck.CheckId, shortenedCheck.CheckId);
        }

        [Fact]
        public void D08_Checks_AreDraftAndPreserveEvidenceIdsVerbatim()
        {
            // 顺序、空格、大小写和重复均有意义；“原样引用”不要求同一集合对象实例。
            var evidence = new[] { "虚构证据:雷达/001", " raw-ID ", "虚构证据:雷达/001", "RAW-id" };
            var report = Analyze(Linear(0, 0, 0, 5, 100), CrossingTarget().Run(100), caseId: "虚构案件-证据", evidence: evidence);
            Assert.NotEmpty(report.RuleChecks);
            Assert.All(report.RuleChecks, c =>
            {
                Assert.Equal(ColregReviewStatus.Draft, c.ReviewStatus);
                Assert.NotNull(c.EvidenceIds);
                Assert.Equal(evidence, c.EvidenceIds.ToArray());
                if (c.AtTimeSec.HasValue) Assert.InRange(c.AtTimeSec.Value, c.StartTime.Seconds, c.EndTime.Seconds);
            });
        }

        [Fact]
        public void D08_DangerStages_ProgressWithoutSplittingLockedSituation()
        {
            // TCPA 700→10 s，DCPA=0；340 s 进入紧迫、640 s 进入紧迫危险。
            var report = Analyze(Linear(0, 0, 0, 5, 690), Linear(0, 7000, 180, 5, 690));
            var band = Assert.Single(report.TimeBands);
            Assert.Equal(EncounterSituation.HeadOn, band.Situation);
            Assert.Equal(ColregDangerStage.ImmediateDanger, band.DangerStage);
            var stages = report.DangerStages.Where(s => s.Stage != ColregDangerStage.None).ToArray();
            Assert.Equal(new[] { ColregDangerStage.CollisionRisk, ColregDangerStage.CloseQuarters, ColregDangerStage.ImmediateDanger }, stages.Select(s => s.Stage).ToArray());
            Assert.Equal(new[] { 0.0, 340.0, 640.0 }, stages.Select(s => s.StartTime.Seconds).ToArray());
            Assert.Equal(new[] { 340.0, 640.0, 690.0 }, stages.Select(s => s.EndTime.Seconds).ToArray());
            AssertIds(stages.Select(s => s.StageId));
        }

        private static ColregAnalysisReport SpeedReviewReport(double speed, double hint, bool inSight)
        {
            return Analyze(Linear(0, 0, 0, speed, 30), Linear(0, (speed + 5) * 300, 180, 5, 30),
                new ColregThresholds(safeSpeedMps: hint), visibility: inSight ? 8 : 0.5, inSight: inSight);
        }

        private static void AssertReviewEvidence(ColregRuleCheck[] checks, double speed, double visibility)
        {
            Assert.NotEmpty(checks);
            Assert.All(checks, c =>
            {
                Assert.Equal(RuleCheckStatus.NeedsReview, c.Status);
                Assert.Equal(visibility, c.Evidence.VisibilityNm, 6);
                Assert.Contains("航速", c.Explanation);
                Assert.Contains(speed.ToString(CultureInfo.InvariantCulture), c.Explanation);
            });
        }

        private static void AssertSubstantial(ColregAnalysisReport report, bool expected)
        {
            var checks = Checks(report, ColregRuleId.R8, Own).Where(c => c.Status != RuleCheckStatus.NotApplicable).ToArray();
            Assert.NotEmpty(checks);
            if (expected)
                Assert.Contains(checks, c => c.Explanation.Contains("明显行动=True") && c.ActualAction.FirstSubstantialActionTime.HasValue);
            else
                Assert.All(checks, c =>
                {
                    Assert.Contains("明显行动=False", c.Explanation);
                    Assert.Null(c.ActualAction.FirstSubstantialActionTime);
                });
        }

        private static void AssertIds(IEnumerable<string> ids)
        {
            var values = ids.ToArray();
            Assert.NotEmpty(values);
            Assert.All(values, id => Assert.False(string.IsNullOrWhiteSpace(id)));
            Assert.Equal(values.Length, values.Distinct(StringComparer.Ordinal).Count());
        }

        private static string MetadataFingerprint(ColregAnalysisReport report)
        {
            // 包含新输出字段，避免仅比较 null==null；非空和唯一性由 AssertIds 单独约束。
            var bands = report.TimeBands.Select(b => FormattableString.Invariant($"B|{b.BandId}|{b.StartTime.Seconds:R}|{b.EndTime.Seconds:R}|{b.Situation}|{b.OwnRole}|{b.TargetRole}|{b.InSight}|{b.GiveWayVesselId}|{b.StandOnVesselId}|{b.Basis}|{b.Doubt}|{b.DangerStage}"));
            var checks = report.RuleChecks.Select(c => FormattableString.Invariant($"C|{c.CheckId}|{c.RuleId}|{c.Clause}|{c.VesselId}|{c.StartTime.Seconds:R}|{c.EndTime.Seconds:R}|{c.Status}|{c.ReviewStatus}|{c.AtTimeSec:R}|{string.Join(",", c.EvidenceIds ?? Array.Empty<string>())}|{c.Explanation}"));
            var stages = report.DangerStages.Select(s => FormattableString.Invariant($"S|{s.StageId}|{s.StartTime.Seconds:R}|{s.EndTime.Seconds:R}|{s.Stage}"));
            return string.Join("\n", bands.Concat(checks).Concat(stages));
        }

        private static ColregAnalysisReport Reciprocal(double dcpaNm, double tcpa, ColregThresholds thresholds = null)
        {
            return Analyze(Linear(0, 0, 0, 5, 0.1), Linear(dcpaNm * MetersPerNm, tcpa * 10, 180, 5, 0.1), thresholds);
        }

        private static ColregAnalysisReport OffBow(double bearing, ColregThresholds thresholds = null)
        {
            return Analyze(Linear(0, 0, 0, 5, 1), Linear(1400 * Sin(bearing), 1400 * Cos(bearing), 180, 5, 1), thresholds);
        }

        private static IEnumerable<ColregRuleCheck> Checks(ColregAnalysisReport report, ColregRuleId rule, string vessel)
        {
            return report.RuleChecks.Where(c => c.RuleId == rule && c.VesselId == vessel);
        }

        private static ColregTimeBand BandAt(ColregAnalysisReport report, double time)
        {
            var band = report.TimeBands.LastOrDefault(b => b.StartTime.Seconds <= time && time <= b.EndTime.Seconds);
            Assert.NotNull(band);
            return band;
        }

        private static ColregAnalysisReport Analyze(IReadOnlyList<TrackSample> own, IReadOnlyList<TrackSample> target,
            ColregThresholds thresholds = null, double? visibility = 8, bool? inSight = true, bool narrow = false,
            IReadOnlyList<EnvironmentState> environment = null, IReadOnlyList<ColregInSightSample> sight = null,
            IReadOnlyList<EnuPosition> channel = null, string caseId = "case", IReadOnlyList<string> evidence = null)
        {
            var request = new ColregAnalysisRequest(Own, Target, own, target, thresholds, environment, visibility, inSight, narrow,
                inSightSamples: sight, channelCenterline: channel, caseId: caseId, evidenceIds: evidence);
            var result = new ColregEngine().Analyze(request);
            Assert.True(result.IsSuccess, result.ErrorCode + " " + result.ErrorMessage);
            return result.Value;
        }

        private static SyntheticShip CrossingTarget() { return new SyntheticShip(2000, 2000, 270, 5); }
        private static ColregInSightSample Sight(double time, bool inSight) { return new ColregInSightSample(new SimTime(time), inSight); }
        private static EnvironmentState Environment(double time, float visibility)
        {
            return new EnvironmentState(new SimTime(time), "返修虚构环境", visibility, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
        }

        private static TrackSample[] Linear(double east, double north, double heading, double speed, double duration)
        {
            return new[] { Sample(0, east, north, heading, speed),
                Sample(duration, east + speed * Sin(heading) * duration, north + speed * Cos(heading) * duration, heading, speed) };
        }

        private static TrackSample Sample(double time, double east, double north, double heading, double speed)
        {
            return new TrackSample(new SimTime(time), new GeoCoord(0, 0), new EnuPosition(east, north),
                new Double2(speed * Sin(heading), speed * Cos(heading)), (float)speed, (float)Normalize(heading),
                (float)Normalize(heading), 0, SampleProvenance.Presumed, TimeQuality.Estimated, false);
        }

        // 消除 sin(180°) 的浮点残差，使 DCPA 严格边界的数据本身保持精确。
        private static double Sin(double angle) { var value = Math.Sin(angle * Math.PI / 180); return Math.Abs(value) < 1e-12 ? 0 : value; }
        private static double Cos(double angle) { var value = Math.Cos(angle * Math.PI / 180); return Math.Abs(value) < 1e-12 ? 0 : value; }
        private static double Normalize(double angle) { return (angle % 360 + 360) % 360; }

        /// <summary>虚构运动学夹具：每秒 6° 连续转向、中点积分、瞬时执行变速指令，每 10 s 输出。</summary>
        private sealed class SyntheticShip
        {
            private readonly double _east, _north, _heading, _speed;
            private readonly List<(double time, double heading, double? speed)> _orders = new List<(double, double, double?)>();

            public SyntheticShip(double east, double north, double heading, double speed)
            {
                _east = east; _north = north; _heading = heading; _speed = speed;
            }

            public SyntheticShip Order(double time, double heading, double? speed = null)
            {
                _orders.Add((time, heading, speed));
                return this;
            }

            public TrackSample[] Run(int duration)
            {
                double east = _east, north = _north, heading = _heading, speed = _speed, command = _heading;
                var orders = _orders.OrderBy(o => o.time).ToArray();
                int next = 0;
                var samples = new List<TrackSample>();
                for (int time = 0; time <= duration; time++)
                {
                    while (next < orders.Length && orders[next].time <= time)
                    {
                        command = orders[next].heading;
                        if (orders[next].speed.HasValue) speed = orders[next].speed.Value;
                        next++;
                    }
                    if (time % 10 == 0 || time == duration) samples.Add(Sample(time, east, north, heading, speed));
                    double delta = Normalize(command - heading + 180) - 180;
                    double step = Math.Sign(delta) * Math.Min(6, Math.Abs(delta));
                    east += speed * Sin(heading + step / 2);
                    north += speed * Cos(heading + step / 2);
                    heading = Normalize(heading + step);
                }
                return samples.ToArray();
            }
        }
    }
}

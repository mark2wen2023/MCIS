using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Colreg;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Xunit;

namespace Mcis.Tests.W1
{
    /// <summary>
    /// W1.1 行为规格：D09–D12，以 2026-11-11 19:46 架构师复测裁定为准。
    /// 全部船名、坐标、状态、时刻都是独立合成的虚构数据；不读取任何案例文件。
    /// 第一阶段失败断言持续约束实现；第二阶段补充非网格时限与窗口折返检查，供外部执行者运行。
    /// </summary>
    public sealed class ColregW11Tests
    {
        private const string Own = "W11虚构甲船";
        private const string Target = "W11虚构乙船";
        private static readonly ColregRuleId[] SectionRules =
            { ColregRuleId.R13, ColregRuleId.R14, ColregRuleId.R15, ColregRuleId.R16, ColregRuleId.R17 };

        [Fact]
        public void D09_R18_IsInCatalogWithResponsibilityTitle()
        {
            Assert.Contains("R18", Enum.GetNames(typeof(ColregRuleId)));
            var rule = Assert.Single(ColregRules.Catalog, r => r.Id == ColregRuleId.R18);
            Assert.Equal("船舶之间的责任", rule.Title);
            Assert.False(string.IsNullOrWhiteSpace(rule.Summary));
        }

        [Theory]
        [InlineData(0)] // 未给序列
        [InlineData(1)] // 空序列
        [InlineData(2)] // 显式 Unknown
        public void D09_UnknownStatus_R18NeedsEvidenceWhileR14StillApplies(int input)
        {
            var status = input == 0 ? null : input == 1 ? Array.Empty<ColregVesselStatusSample>() :
                Statuses(ColregVesselStatus.Unknown, ColregVesselStatus.Unknown);
            var report = Analyze(HeadOnRequest(status: status));
            Assert.Equal(EncounterSituation.HeadOn, BandAt(report, 0).Situation);
            foreach (string vessel in new[] { Own, Target })
            {
                Assert.Contains(Checks(report, ColregRuleId.R14, vessel), c => c.Status != RuleCheckStatus.NotApplicable);
                var r18 = Checks(report, ColregRuleId.R18, vessel).ToArray();
                Assert.NotEmpty(r18);
                Assert.All(r18, c =>
                {
                    Assert.Equal(RuleCheckStatus.NotAssessable, c.Status);
                    foreach (string evidence in new[] { "号灯", "号型", "VHF", "VDR", "音频", "轮机日志" })
                        Assert.Contains(evidence, c.Explanation);
                });
            }
            AssertStatuses(BandAt(report, 0), ColregVesselStatus.Unknown, ColregVesselStatus.Unknown);
            Assert.Contains(report.Assumptions, a => a.Contains("Unknown") && a.Contains("机动船"));
        }

        [Theory]
        [InlineData(ColregVesselStatus.NotUnderCommand, ColregVesselStatus.PowerDriven)]
        [InlineData(ColregVesselStatus.NotUnderCommand, ColregVesselStatus.Unknown)]
        [InlineData(ColregVesselStatus.RestrictedManoeuvrability, ColregVesselStatus.PowerDriven)]
        [InlineData(ColregVesselStatus.RestrictedManoeuvrability, ColregVesselStatus.Unknown)]
        public void D09_NucOrRam_HasNoStandOnDutyAndOtherVesselGivesWay(
            ColregVesselStatus privileged, ColregVesselStatus other)
        {
            var request = HeadOnRequest(status: Statuses(privileged, other));
            foreach (var ordered in new[] { request, Swap(request) })
            {
                var report = Analyze(ordered);
                var band = BandAt(report, 0);
                Assert.Equal(Target, band.GiveWayVesselId);
                Assert.Null(band.StandOnVesselId);
                Assert.Equal(TrafficRole.None, RoleOf(band, ordered, Own));
                Assert.Equal(TrafficRole.GiveWay, RoleOf(band, ordered, Target));
                AssertStatuses(band, privileged, other);
                Assert.Contains(ColregRuleId.R18, band.ApplicableRules);
                AssertRuleStatuses(report, Own, 0, 100, RuleCheckStatus.NotApplicable,
                    ColregRuleId.R14, ColregRuleId.R15, ColregRuleId.R16, ColregRuleId.R17);
                var explanation = string.Join(" ", report.RuleChecks.Where(c => c.VesselId == Own &&
                    new[] { ColregRuleId.R14, ColregRuleId.R15, ColregRuleId.R16, ColregRuleId.R17 }.Contains(c.RuleId))
                    .Select(c => c.Explanation));
                Assert.Contains("R18", explanation);
                Assert.Contains(privileged == ColregVesselStatus.NotUnderCommand ? "失控" : "操限", explanation);
                Assert.Contains("无直航义务", band.Basis);
                // 他船全程无避让行动：不能因原几何为对遇而漏掉 R16/R18(a)。
                Assert.Contains(Checks(report, ColregRuleId.R16, Target), c => c.Status == RuleCheckStatus.NotSatisfied);
                Assert.Contains(Checks(report, ColregRuleId.R18, Target), c => c.Clause.StartsWith("R18(a)", StringComparison.Ordinal)
                    && c.Status == RuleCheckStatus.NotSatisfied);
                AssertGeneralChecksRemain(report, Own, 0, 100);
            }
        }

        [Theory]
        [InlineData(ColregVesselStatus.NotUnderCommand, ColregVesselStatus.RestrictedManoeuvrability)]
        [InlineData(ColregVesselStatus.NotUnderCommand, ColregVesselStatus.NotUnderCommand)]
        [InlineData(ColregVesselStatus.RestrictedManoeuvrability, ColregVesselStatus.RestrictedManoeuvrability)]
        [InlineData(ColregVesselStatus.ConstrainedByDraught, ColregVesselStatus.PowerDriven)]
        [InlineData(ColregVesselStatus.Fishing, ColregVesselStatus.PowerDriven)]
        [InlineData(ColregVesselStatus.Sailing, ColregVesselStatus.PowerDriven)]
        public void D09_UnsupportedStatusPairs_R18NeedsReviewWithNullResponsibilities(
            ColregVesselStatus own, ColregVesselStatus target)
        {
            var request = HeadOnRequest(status: Statuses(own, target));
            foreach (var ordered in new[] { request, Swap(request) })
            {
                var report = Analyze(ordered);
                var band = BandAt(report, 0);
                Assert.Null(band.GiveWayVesselId);
                Assert.Null(band.StandOnVesselId);
                var checks = report.RuleChecks.Where(c => c.RuleId == ColregRuleId.R18).ToArray();
                Assert.NotEmpty(checks);
                Assert.All(checks, c =>
                {
                    Assert.Equal(RuleCheckStatus.NeedsReview, c.Status);
                    Assert.False(string.IsNullOrWhiteSpace(c.Explanation));
                });
            }
        }

        [Theory]
        [InlineData(40.0)] // 同船重复
        [InlineData(30.0)] // 同船倒序
        public void D09_StatusSamples_MustIncreaseStrictlyPerVessel(double second)
        {
            var status = new[] { Status(Own, 40, ColregVesselStatus.PowerDriven),
                Status(Target, 0, ColregVesselStatus.PowerDriven),
                Status(Own, second, ColregVesselStatus.NotUnderCommand) };
            var result = new ColregEngine().Analyze(HeadOnRequest(status: status));
            Assert.False(result.IsSuccess);
            Assert.Equal("COLREG_INVALID_INPUT", result.ErrorCode);
        }

        [Fact]
        public void D09_StatusSamples_InterleavingStepHoldAndRequestSnapshot()
        {
            // 全局时间不递增，但同船严格递增；首个样本前必须 Unknown，不能向过去填充。
            var status = new List<ColregVesselStatusSample> {
                Status(Own, 20, ColregVesselStatus.PowerDriven), Status(Own, 103.25, ColregVesselStatus.NotUnderCommand),
                Status(Target, 0, ColregVesselStatus.PowerDriven) };
            var request = HeadOnRequest(duration: 200, status: status);
            status[1] = Status(Own, 103.25, ColregVesselStatus.Sailing);
            status.Clear();
            var report = Analyze(request);
            AssertStatuses(BandAt(report, 0), ColregVesselStatus.Unknown, ColregVesselStatus.PowerDriven);
            AssertStatuses(BandAt(report, 20), ColregVesselStatus.PowerDriven, ColregVesselStatus.PowerDriven);
            AssertStatuses(BandAt(report, 103.249), ColregVesselStatus.PowerDriven, ColregVesselStatus.PowerDriven);
            AssertStatuses(BandAt(report, 103.25), ColregVesselStatus.NotUnderCommand, ColregVesselStatus.PowerDriven);
            AssertStatuses(BandAt(report, 199), ColregVesselStatus.NotUnderCommand, ColregVesselStatus.PowerDriven);
        }

        [Fact]
        public void D09_StatusTransitions_SplitExactlyAndReclassifyOnRecovery()
        {
            var status = new[] { Status(Own, 0, ColregVesselStatus.PowerDriven),
                Status(Target, 0, ColregVesselStatus.PowerDriven),
                Status(Own, 103.25, ColregVesselStatus.NotUnderCommand),
                Status(Own, 181.75, ColregVesselStatus.PowerDriven) };
            var report = Analyze(HeadOnRequest(duration: 250, status: status));
            Assert.Equal(new[] { 0.0, 103.25, 181.75 }, report.TimeBands.Select(b => b.StartTime.Seconds).ToArray());
            Assert.Equal(new[] { 103.25, 181.75, 250.0 }, report.TimeBands.Select(b => b.EndTime.Seconds).ToArray());
            Assert.Equal(TrafficRole.BothActionRequired, BandAt(report, 103.249).OwnRole);
            Assert.Equal(TrafficRole.None, BandAt(report, 103.25).OwnRole);
            Assert.Equal(Target, BandAt(report, 103.25).GiveWayVesselId);
            Assert.Equal(EncounterSituation.HeadOn, BandAt(report, 181.75).Situation);
            Assert.Equal(TrafficRole.BothActionRequired, BandAt(report, 181.75).OwnRole);
            Assert.Contains(Checks(report, ColregRuleId.R14, Own), c => c.StartTime.Seconds == 181.75 &&
                c.Status != RuleCheckStatus.NotApplicable);
        }

        [Fact]
        public void D09_StatusChangeWhilePending_EstablishesR18ResponsibilityImmediately()
        {
            var geometry = DeferredRequest();
            var status = new[] { Status(Own, 0, ColregVesselStatus.PowerDriven),
                Status(Target, 0, ColregVesselStatus.PowerDriven), Status(Own, 73.25, ColregVesselStatus.NotUnderCommand) };
            var report = Analyze(new ColregAnalysisRequest(Own, Target, geometry.OwnSamples, geometry.TargetSamples,
                vesselsInSight: true, vesselStatusSamples: status));
            AssertPending(BandAt(report, 73.249));
            var changed = BandAt(report, 73.25);
            Assert.Equal(73.25, changed.StartTime.Seconds);
            Assert.Equal(Target, changed.GiveWayVesselId);
            Assert.Null(changed.StandOnVesselId);
            Assert.Equal(TrafficRole.None, changed.OwnRole);
            Assert.Equal(TrafficRole.GiveWay, changed.TargetRole);
            AssertStatuses(changed, ColregVesselStatus.NotUnderCommand, ColregVesselStatus.PowerDriven);
            AssertRuleStatuses(report, Own, 73.25, 100, RuleCheckStatus.NotApplicable,
                ColregRuleId.R14, ColregRuleId.R15, ColregRuleId.R16, ColregRuleId.R17);
        }

        [Fact]
        public void D09_OvertakingNuc_R13KeepsOtherVesselAsGiveWay()
        {
            var request = new ColregAnalysisRequest(Own, Target, Linear(0, 0, 0, 5, 100),
                Linear(100, -1000, 0, 10, 100), vesselsInSight: true,
                vesselStatusSamples: Statuses(ColregVesselStatus.NotUnderCommand, ColregVesselStatus.PowerDriven));
            var report = Analyze(request);
            var band = BandAt(report, 0);
            Assert.Equal(EncounterSituation.Overtaking, band.Situation);
            Assert.Equal(Target, band.GiveWayVesselId);
            Assert.Null(band.StandOnVesselId);
            Assert.Equal(TrafficRole.None, band.OwnRole);
            Assert.Equal(TrafficRole.GiveWay, band.TargetRole);
            Assert.Contains(Checks(report, ColregRuleId.R13, Target), c => c.Status != RuleCheckStatus.NotApplicable);
            Assert.Contains(ColregRuleId.R18, band.ApplicableRules);
        }

        [Fact]
        public void D09_StatusChangeAfterCpa_PreservesOvertakingUntilClear()
        {
            // 200s过CPA，250s仍距约269m，390s才达到0.5nm让清距离；状态变化不能提前解除R13。
            var request = new ColregAnalysisRequest(Own, Target, Linear(0, 0, 0, 5, 500),
                Linear(100, -1000, 0, 10, 500), vesselsInSight: true,
                vesselStatusSamples: new[] { Status(Own, 0, ColregVesselStatus.PowerDriven),
                    Status(Target, 0, ColregVesselStatus.PowerDriven), Status(Own, 250, ColregVesselStatus.NotUnderCommand) });
            foreach (var ordered in new[] { request, Swap(request) })
            {
                var report = Analyze(ordered);
                var band = BandAt(report, 250);
                Assert.Equal(250, band.StartTime.Seconds, 9);
                Assert.Equal(EncounterSituation.Overtaking, band.Situation);
                Assert.Equal(Target, band.GiveWayVesselId);
                Assert.Null(band.StandOnVesselId);
                Assert.Equal(TrafficRole.None, RoleOf(band, ordered, Own));
                Assert.Equal(TrafficRole.GiveWay, RoleOf(band, ordered, Target));
                Assert.Equal(390, band.EndTime.Seconds, 9);
                Assert.Contains(Checks(report, ColregRuleId.R18, Target), c => c.StartTime.Seconds == 250 &&
                    c.Status != RuleCheckStatus.NotApplicable);
                Assert.Equal(EncounterSituation.NoCollisionRisk, BandAt(report, 400).Situation);
            }
        }

        [Fact]
        public void D09_NucInRestrictedVisibility_R19AndGeneralChecksRemain()
        {
            var report = Analyze(HeadOnRequest(inSight: false,
                status: Statuses(ColregVesselStatus.NotUnderCommand, ColregVesselStatus.PowerDriven)));
            Assert.Equal(EncounterSituation.RestrictedVisibility, BandAt(report, 0).Situation);
            AssertStatuses(BandAt(report, 0), ColregVesselStatus.NotUnderCommand, ColregVesselStatus.PowerDriven);
            AssertGeneralChecksRemain(report, Own, 0, 100);
            Assert.Contains(Checks(report, ColregRuleId.R19, Own), c => c.Status != RuleCheckStatus.NotApplicable);
            AssertRuleStatuses(report, Own, 0, 100, RuleCheckStatus.NotApplicable,
                ColregRuleId.R14, ColregRuleId.R15, ColregRuleId.R16, ColregRuleId.R17);
        }

        [Fact]
        public void D09_SyntheticHailiFiction5_NucThenPortTurnIsNotAnR14Violation()
        {
            const string haili = "海力虚构5", a17 = "虚构A17";
            const double nucTime = 103.25;
            var own = Integrate(0, 0, t => t <= 130 ? 0 : -Math.Min(30, (t - 130) * 3), 5, 250);
            var target = Linear(0, 4000, 180, 5, 250);
            var status = new[] { Status(haili, 0, ColregVesselStatus.PowerDriven),
                Status(a17, 0, ColregVesselStatus.PowerDriven), Status(haili, nucTime, ColregVesselStatus.NotUnderCommand) };
            var report = Analyze(new ColregAnalysisRequest(haili, a17, own, target, vesselsInSight: true,
                vesselStatusSamples: status, caseId: "完全合成-W11-NUC"));
            var before = BandAt(report, nucTime - 0.001);
            Assert.Equal(EncounterSituation.HeadOn, before.Situation);
            Assert.Equal(nucTime, before.EndTime.Seconds, 9);
            Assert.Contains(Checks(report, ColregRuleId.R14, haili), c => c.StartTime.Seconds < nucTime &&
                c.EndTime.Seconds == nucTime && c.Status != RuleCheckStatus.NotApplicable);
            var after = report.TimeBands.Where(b => b.StartTime.Seconds >= nucTime).ToArray();
            Assert.NotEmpty(after);
            Assert.Equal(nucTime, after[0].StartTime.Seconds, 9);
            Assert.All(after, b =>
            {
                Assert.Equal(a17, b.GiveWayVesselId);
                Assert.Null(b.StandOnVesselId);
                Assert.Equal(TrafficRole.None, b.OwnRole);
                Assert.Equal(2, b.VesselStatus.Count);
                Assert.Equal(ColregVesselStatus.NotUnderCommand, b.VesselStatus[haili]);
                Assert.Equal(ColregVesselStatus.PowerDriven, b.VesselStatus[a17]);
            });
            AssertRuleStatuses(report, haili, nucTime, 250, RuleCheckStatus.NotApplicable,
                ColregRuleId.R14, ColregRuleId.R15, ColregRuleId.R16, ColregRuleId.R17);
            AssertGeneralChecksRemain(report, haili, nucTime, 250);
            Assert.Contains(Checks(report, ColregRuleId.R8, haili), c => c.StartTime.Seconds >= nucTime &&
                c.ActualAction.MaxPortTurnDeg >= 29);
            Assert.Contains(Checks(report, ColregRuleId.R18, a17), c => c.StartTime.Seconds == nucTime &&
                c.Status != RuleCheckStatus.NotApplicable);
        }

        [Theory]
        [InlineData(20.0, 174.0)]
        [InlineData(-20.0, 186.0)]
        public void D10_EitherDoubtView_IsHeadOnInBothOrders(double bearing, double heading)
        {
            // 20°/26°（或其镜像），接近反向偏差恰为 6°。
            var request = OffBow(bearing, heading);
            foreach (var ordered in new[] { request, Swap(request) })
            {
                var band = BandAt(Analyze(ordered), 0);
                Assert.Equal(EncounterSituation.HeadOn, band.Situation);
                Assert.True(band.Doubt);
                Assert.Equal(ColregDoubtReasons.HeadOnDoubt, band.DoubtReason);
                Assert.Equal(TrafficRole.BothActionRequired, band.OwnRole);
                Assert.Equal(TrafficRole.BothActionRequired, band.TargetRole);
            }
        }

        [Fact]
        public void D10_EitherForwardView_IsHeadOnWithoutDoubt()
        {
            // 甲看乙 14°，乙看甲 20°：任一明确前方视角已足够，不落入“否则存疑”分支。
            var request = OffBow(14, 174);
            foreach (var ordered in new[] { request, Swap(request) })
            {
                var band = BandAt(Analyze(ordered), 0);
                Assert.Equal(EncounterSituation.HeadOn, band.Situation);
                Assert.False(band.Doubt);
                Assert.Null(band.DoubtReason);
            }
        }

        [Theory]
        [InlineData(15.0, 180.0, 22.5, EncounterSituation.HeadOn, false)]
        [InlineData(22.5, 180.0, 22.5, EncounterSituation.HeadOn, true)]
        [InlineData(22.51, 180.0, 22.5, EncounterSituation.Crossing, true)]
        [InlineData(25.0, 180.0, 22.5, EncounterSituation.Crossing, true)]
        [InlineData(25.0, 180.0, 30.0, EncounterSituation.HeadOn, true)]
        [InlineData(10.0, 188.0, 22.5, EncounterSituation.Crossing, true)]
        public void D10_DoubtBoundariesAndHeadingPrerequisite_ArePreserved(double bearing, double heading,
            double doubtBearing, EncounterSituation situation, bool doubt)
        {
            var request = OffBow(bearing, heading, new ColregThresholds(headOnDoubtBearingDeg: doubtBearing));
            foreach (var ordered in new[] { request, Swap(request) })
            {
                var band = BandAt(Analyze(ordered), 0);
                Assert.Equal(situation, band.Situation);
                Assert.Equal(doubt, band.Doubt);
                if (situation == EncounterSituation.HeadOn && doubt)
                    Assert.Equal(ColregDoubtReasons.HeadOnDoubt, band.DoubtReason);
            }
        }

        [Theory]
        [InlineData(30.0, 200.0, "右舷", "让路")]
        [InlineData(-30.0, 160.0, "左舷", "直航")]
        public void D11_ContradictoryViews_HaveNullIdsUndeterminedRolesAndBothBases(
            double bearing, double heading, string side, string action)
        {
            var request = OffBow(bearing, heading, duration: 150);
            foreach (var ordered in new[] { request, Swap(request) })
            {
                var band = BandAt(Analyze(ordered), 0);
                Assert.Equal(EncounterSituation.Crossing, band.Situation);
                Assert.True(band.Doubt);
                Assert.Equal(ColregDoubtReasons.ContradictoryViews, band.DoubtReason);
                Assert.Null(band.GiveWayVesselId);
                Assert.Null(band.StandOnVesselId);
                Assert.Equal(TrafficRole.Undetermined, band.OwnRole);
                Assert.Equal(TrafficRole.Undetermined, band.TargetRole);
                Assert.Contains("本船视角", band.Basis);
                Assert.Contains("他船视角", band.Basis);
                // 各视角必须各自说明方位和结论，不能只写笼统“矛盾”。
                foreach (string view in new[] { "本船视角", "他船视角" })
                {
                    string conclusion = band.Basis.Substring(band.Basis.IndexOf(view, StringComparison.Ordinal))
                        .Split(new[] { '；', ';', '。', '\n' })[0];
                    Assert.Contains(side, conclusion);
                    Assert.Contains(action, conclusion);
                }
            }
        }

        [Theory]
        [InlineData(30.0, 200.0)]
        [InlineData(-30.0, 160.0)]
        public void D11_BothVesselsR15R16R17_NeedReviewWhileR8StillRuns(double bearing, double heading)
        {
            // 裁定优先：只读验收 A3_ContradictoryViews_FlaggedDoubt 仍要求 Partial，与此处冲突。
            var report = Analyze(OffBow(bearing, heading, duration: 150));
            foreach (string vessel in new[] { Own, Target })
            {
                AssertRuleStatuses(report, vessel, 0, 150, RuleCheckStatus.NeedsReview,
                    ColregRuleId.R15, ColregRuleId.R16, ColregRuleId.R17);
                AssertGeneralChecksRemain(report, vessel, 0, 150);
            }
        }

        public static IEnumerable<object[]> SwapGrid()
        {
            // 确定性笛卡尔积，1620 行；无随机数。覆盖跨零、双侧边界、同侧矛盾、横距、追越、未互见与 NUC 切换。
            foreach (double rotation in new[] { 0.0, 45, 90, 180, 270, 359 })
            foreach (double bearing in new[] { 0.0, 15, 20, 22.5, 25, 30, 180, 330, 340 })
            foreach (double offset in new[] { -180.0, -20, -6, 0, 8 })
            foreach (double lateral in new[] { 0.0, 300 })
            foreach (int mode in new[] { 0, 1, 2 })
                yield return new object[] { rotation, bearing, offset, lateral, mode };
        }

        [Theory]
        [MemberData(nameof(SwapGrid))]
        public void D10_D11_SwapGrid_PreservesBandsVesselRolesAndCheckStatusMultiset(
            double rotation, double bearing, double offset, double lateral, int mode)
        {
            double localEast = 2000 * Sin(bearing) + lateral, localNorth = 2000 * Cos(bearing);
            var own = Linear(0, 0, rotation, 5, 40);
            var target = Linear(localEast * Cos(rotation) + localNorth * Sin(rotation),
                -localEast * Sin(rotation) + localNorth * Cos(rotation), rotation + 180 + offset,
                offset == -180 ? 10 : 5, 40);
            var status = mode == 0 ? null : mode == 1 ? Statuses(ColregVesselStatus.PowerDriven, ColregVesselStatus.PowerDriven) :
                new[] { Status(Own, 0, ColregVesselStatus.PowerDriven), Status(Target, 0, ColregVesselStatus.PowerDriven),
                    Status(Own, 17.25, ColregVesselStatus.NotUnderCommand) };
            var request = new ColregAnalysisRequest(Own, Target, own, target,
                visibilityNm: mode == 1 ? 0.5 : 8, vesselsInSight: mode != 1,
                vesselStatusSamples: status, caseId: "虚构-W11-交换性质");
            var ab = Analyze(request);
            var ba = Analyze(Swap(request));
            Assert.Equal(ab.TimeBands.Count, ba.TimeBands.Count);
            for (int i = 0; i < ab.TimeBands.Count; i++)
            {
                var a = ab.TimeBands[i]; var b = ba.TimeBands[i];
                Assert.Equal(a.StartTime, b.StartTime);
                Assert.Equal(a.EndTime, b.EndTime);
                Assert.Equal(a.Situation, b.Situation);
                Assert.Equal(a.Doubt, b.Doubt);
                Assert.Equal(a.DoubtReason, b.DoubtReason);
                Assert.Equal(a.InSight, b.InSight);
                Assert.Equal(a.DangerStage, b.DangerStage);
                Assert.Equal(a.GiveWayVesselId, b.GiveWayVesselId);
                Assert.Equal(a.StandOnVesselId, b.StandOnVesselId);
                Assert.Equal(a.OwnRole, b.TargetRole);
                Assert.Equal(a.TargetRole, b.OwnRole);
                Assert.Equal(a.VesselStatus.OrderBy(p => p.Key, StringComparer.Ordinal).ToArray(),
                    b.VesselStatus.OrderBy(p => p.Key, StringComparer.Ordinal).ToArray());
            }
            // 键=(RuleId,Clause,VesselId,StartTime,EndTime)，排序后保留每一项与重复项；不比较顺序相关的 ID。
            Assert.Equal(CheckStatuses(ab), CheckStatuses(ba));
        }

        [Theory]
        [InlineData(false)]
        [InlineData(true)]
        public void D12_TurningEitherVessel_DefersUntilBothHeadingsAreStable(bool turnOwn)
        {
            // ENU/COG 为对驶，TCPA=780-t，t=60 首次进入720s风险窗。
            // HDG 独立于 COG（合成偏航/侧滑），0–50s 转20°：t=90回看变化8°，t=100仅4°。
            var report = Analyze(DeferredRequest(turnOwn: turnOwn));
            Assert.Equal(EncounterSituation.NoCollisionRisk, BandAt(report, 50).Situation);
            var pending = BandAt(report, 60);
            AssertPending(pending);
            Assert.Equal(60, pending.StartTime.Seconds);
            Assert.Equal(100, pending.EndTime.Seconds);
            AssertPending(BandAt(report, 90));
            var locked = BandAt(report, 100);
            Assert.Equal(EncounterSituation.HeadOn, locked.Situation);
            Assert.False(locked.Doubt);
            Assert.Null(locked.DoubtReason);
            foreach (string vessel in new[] { Own, Target })
            {
                AssertRuleStatuses(report, vessel, 60, 100, RuleCheckStatus.NeedsReview, SectionRules);
                AssertGeneralChecksRemain(report, vessel, 60, 100);
                var r18 = Checks(report, ColregRuleId.R18, vessel).Where(c => Overlaps(c, 60, 100)).ToArray();
                Assert.NotEmpty(r18);
                Assert.All(r18, c => Assert.Equal(RuleCheckStatus.NotAssessable, c.Status));
                Assert.Contains(report.RuleChecks, c => c.VesselId == vessel && Overlaps(c, 60, 100) &&
                    c.Explanation.Contains("转向中") && c.Explanation.Contains("延后"));
            }
        }

        [Fact]
        public void D12_StillTurningAfter120Seconds_LocksWithLockedDuringTurnAndStaysLocked()
        {
            Func<double, double> heading = t => t <= 180 ? 160 + t / 6 : t <= 210 ? 190 - (t - 180) / 3 : 180;
            var report = Analyze(DeferredRequest(targetHeading: heading, duration: 300));
            AssertPending(BandAt(report, 60));
            AssertPending(BandAt(report, 179.999));
            var locked = BandAt(report, 180); // 从首次风险60s起120s，不能从观测0s计时。
            Assert.Equal(180, locked.StartTime.Seconds);
            Assert.Equal(EncounterSituation.Crossing, locked.Situation); // 此刻HDG190°，尚非对遇。
            Assert.True(locked.Doubt);
            Assert.Equal(ColregDoubtReasons.LockedDuringTurn, locked.DoubtReason);
            Assert.Equal(Own, locked.GiveWayVesselId);
            Assert.All(report.TimeBands.Where(b => b.StartTime.Seconds >= 180), b =>
            {
                Assert.Equal(EncounterSituation.Crossing, b.Situation);
                Assert.Equal(ColregDoubtReasons.LockedDuringTurn, b.DoubtReason);
                Assert.True(b.Doubt);
            });
            Assert.Equal(EncounterSituation.Crossing, BandAt(report, 290).Situation); // 后来稳定于180°也不重判。
        }

        [Theory]
        [InlineData(60.0, 5.0, 120.0, 100.0, false)]
        [InlineData(30.0, 5.0, 120.0, 70.0, false)]
        [InlineData(60.0, 10.0, 120.0, 90.0, false)]
        [InlineData(60.0, 5.0, 20.0, 80.0, true)]
        public void D12_StableWindowChangeAndMaximumDeferral_AreConfigurable(double window, double change,
            double defer, double lockTime, bool forced)
        {
            var thresholds = new ColregThresholds(lockHeadingStableWindowSeconds: window,
                lockHeadingStableMaxChangeDeg: change, lockMaxDeferSeconds: defer);
            var report = Analyze(DeferredRequest(thresholds: thresholds));
            AssertPending(BandAt(report, 60));
            Assert.Equal(lockTime, BandAt(report, 60).EndTime.Seconds);
            var locked = BandAt(report, lockTime);
            Assert.Equal(EncounterSituation.HeadOn, locked.Situation);
            Assert.Equal(forced, locked.Doubt);
            Assert.Equal(forced ? ColregDoubtReasons.LockedDuringTurn : null, locked.DoubtReason);
            Assert.Equal(window, report.Thresholds.LockHeadingStableWindowSeconds);
            Assert.Equal(change, report.Thresholds.LockHeadingStableMaxChangeDeg);
            Assert.Equal(defer, report.Thresholds.LockMaxDeferSeconds);
        }

        [Theory]
        [InlineData(175.0, 180.0)] // 恰5°可锁，不能写成>=5°就推迟。
        [InlineData(358.0, 362.0)] // 跨零仅4°，不能误算356°。
        public void D12_FiveDegreeBoundaryAndHeadingWrap_DoNotDefer(double from, double to)
        {
            var heading = new Func<double, double>(t => from + (to - from) * Math.Min(t, 50) / 50);
            var report = Analyze(DeferredRequest(targetHeading: heading));
            Assert.Equal(60, report.TimeBands.First(b => b.Situation != EncounterSituation.NoCollisionRisk).StartTime.Seconds);
            Assert.DoesNotContain(report.TimeBands, b => b.Situation == EncounterSituation.Undetermined);
        }

        [Fact]
        public void D12_NonGridMaximumDeferral_LocksAtExactDeadline()
        {
            var report = Analyze(DeferredRequest(thresholds: new ColregThresholds(lockMaxDeferSeconds: 17.25)));
            AssertPending(BandAt(report, 60));
            Assert.Equal(77.25, BandAt(report, 60).EndTime.Seconds, 9);
            var locked = BandAt(report, 77.25);
            Assert.Equal(77.25, locked.StartTime.Seconds, 9);
            Assert.Equal(EncounterSituation.HeadOn, locked.Situation);
            Assert.True(locked.Doubt);
            Assert.Equal(ColregDoubtReasons.LockedDuringTurn, locked.DoubtReason);
        }

        [Fact]
        public void D12_HeadingExcursionReturningToOrigin_IsNotStable()
        {
            // t=60首次形成危险时，窗口两端都是180°，但期间曾偏转20°；不可只比较净航向差。
            Func<double, double> heading = t => t <= 30 ? 180 + t * 2 / 3 :
                t <= 60 ? 200 - (t - 30) * 2 / 3 : 180;
            var report = Analyze(DeferredRequest(targetHeading: heading));
            AssertPending(BandAt(report, 60));
            AssertPending(BandAt(report, 110));
            var locked = BandAt(report, 120);
            Assert.Equal(120, locked.StartTime.Seconds, 9);
            Assert.Equal(EncounterSituation.HeadOn, locked.Situation);
            Assert.False(locked.Doubt);
            Assert.Null(locked.DoubtReason);
        }

        [Fact]
        public void D12_PendingHistory_IsNotRewrittenByLaterStableSamples()
        {
            var prefix = Analyze(DeferredRequest(duration: 90));
            var complete = Analyze(DeferredRequest(duration: 200));
            foreach (double time in new[] { 60.0, 70, 80, 89 })
            {
                AssertPending(BandAt(prefix, time));
                AssertPending(BandAt(complete, time));
            }
            Assert.Equal(90, prefix.TimeBands.Last().EndTime.Seconds);
            Assert.Equal(100, BandAt(complete, 70).EndTime.Seconds);
            Assert.Equal(EncounterSituation.HeadOn, BandAt(complete, 100).Situation);
        }

        [Fact]
        public void D12_FirstSampleRisk_UsesAvailableHistoryWithoutLookingAhead()
        {
            // 首帧历史只有一个值，变化为0；未来转向不能用于回判t=0为pending。
            var own = Linear(0, 0, 0, 5, 100);
            var target = GroundTrack(0, 4000, 180, 5, t => 180 + Math.Min(30, t), 100);
            var prefix = Analyze(new ColregAnalysisRequest(Own, Target, new[] { own[0] }, new[] { target[0] }, vesselsInSight: true));
            var complete = Analyze(new ColregAnalysisRequest(Own, Target, own, target, vesselsInSight: true));
            Assert.Equal(EncounterSituation.HeadOn, BandAt(prefix, 0).Situation);
            Assert.Equal(EncounterSituation.HeadOn, BandAt(complete, 0).Situation);
            Assert.DoesNotContain(complete.TimeBands, b => b.Situation == EncounterSituation.Undetermined);
        }

        [Fact]
        public void D12_StableLock_IsNotReclassifiedWhenTurningResumes()
        {
            Func<double, double> heading = t => t < 50 ? 160 + 0.4 * t : t <= 120 ? 180 : 180 + Math.Min(30, t - 120);
            var report = Analyze(DeferredRequest(targetHeading: heading, duration: 250));
            AssertPending(BandAt(report, 60));
            Assert.Equal(100, BandAt(report, 100).StartTime.Seconds);
            Assert.All(report.TimeBands.Where(b => b.StartTime.Seconds >= 100), b =>
            {
                Assert.Equal(EncounterSituation.HeadOn, b.Situation);
                Assert.Equal(TrafficRole.BothActionRequired, b.OwnRole);
                Assert.Equal(TrafficRole.BothActionRequired, b.TargetRole);
            });
        }

        [Fact]
        public void D12_RiskReformsDuringTurn_DefersTheNewEncounter()
        {
            // 独立合成的掉头；已知验收 TimeBands_MultipleTransitions 的 Crossing 预期与新裁定冲突。
            var own = Linear(0, 0, 0, 5, 900);
            var target = Integrate(30, -1000, t => t <= 500 ? 0 : -Math.Min(180, (t - 500) * 6), 10, 900);
            var report = Analyze(new ColregAnalysisRequest(Own, Target, own, target, vesselsInSight: true));
            Assert.Equal(EncounterSituation.Overtaking, BandAt(report, 0).Situation);
            Assert.Equal(EncounterSituation.NoCollisionRisk, BandAt(report, 450).Situation);
            AssertPending(BandAt(report, 520));
            AssertPending(BandAt(report, 580));
            Assert.Equal(EncounterSituation.HeadOn, BandAt(report, 590).Situation);
            Assert.DoesNotContain(report.TimeBands, b => b.StartTime.Seconds >= 500 && b.Situation == EncounterSituation.Crossing);
        }

        [Fact]
        public void D12_BecomingVisibleDuringTurn_DefersAtTheExactSightBoundary()
        {
            Func<double, double> heading = t => t <= 60 ? 180 : 180 - Math.Min(20, (t - 60) * 2 / 3);
            var request = new ColregAnalysisRequest(Own, Target,
                Linear(0, 0, 0, 5, 250), GroundTrack(0, 7800, 180, 5, heading, 250),
                vesselsInSight: false, inSightSamples: new[] {
                    new ColregInSightSample(new SimTime(0), false), new ColregInSightSample(new SimTime(103), true) });
            var report = Analyze(request);
            Assert.Equal(EncounterSituation.RestrictedVisibility, BandAt(report, 102.999).Situation);
            var pending = BandAt(report, 103);
            AssertPending(pending);
            Assert.Equal(103, pending.StartTime.Seconds);
            Assert.Equal(true, pending.InSight);
            AssertPending(BandAt(report, 140));
            Assert.Equal(EncounterSituation.Crossing, BandAt(report, 150).Situation);
            Assert.Contains(Checks(report, ColregRuleId.R19, Own), c => c.EndTime.Seconds == 103 &&
                c.Status != RuleCheckStatus.NotApplicable);
        }

        [Fact]
        public void D12_EarlyActionOrigin_IsFirstRiskAndKeepsActionsTakenWhilePending()
        {
            // TCPA=780-t，风险起点60s；甲HDG在40–100s左转60°，60s后首次再转够30°于90s。
            // 160s才稳定锁为交叉。乙110s加速，使锁定帧TCPA与首次风险基准不同；90s的行动不能丢失。
            Func<double, double> heading = t => -Math.Max(0, Math.Min(60, t - 40));
            var own = GroundTrack(0, 0, 0, 5, heading, 250);
            var target = Enumerable.Range(0, 26).Select(i =>
            {
                double time = i * 10, travel = 5 * Math.Min(time, 110) + 6 * Math.Max(0, time - 110);
                return Sample(time, 3900 - travel, 3900, 270, time < 110 ? 5 : 6, 270);
            }).ToArray();
            var report = Analyze(new ColregAnalysisRequest(Own, Target, own, target, vesselsInSight: true));
            AssertPending(BandAt(report, 60));
            var locked = BandAt(report, 160);
            Assert.Equal(EncounterSituation.Crossing, locked.Situation);
            Assert.Equal(Own, locked.GiveWayVesselId);
            foreach (var rule in new[] { ColregRuleId.R16, ColregRuleId.R8 })
            {
                var checks = Checks(report, rule, Own).Where(c => c.EndTime.Seconds > locked.StartTime.Seconds &&
                    c.Status != RuleCheckStatus.NotApplicable).ToArray();
                Assert.NotEmpty(checks);
                Assert.Contains(checks, c => c.ActualAction.FirstSubstantialActionTime.HasValue &&
                    Math.Abs(c.ActualAction.FirstSubstantialActionTime.Value.Seconds - 90) < 1e-6 &&
                    Math.Abs(c.Evidence.EarlyActionRemainingTcpaSeconds - 690) < 1e-6);
            }
            Assert.Contains(report.Assumptions, a => a.Contains("及早") && a.Contains("首次") &&
                (a.Contains("风险") || a.Contains("危险")));
        }

        [Fact]
        public void Contract_BandFields_ExposeBothStatusesAndNullReasonWhenNotInDoubt()
        {
            var report = Analyze(HeadOnRequest(status: Statuses(ColregVesselStatus.PowerDriven, ColregVesselStatus.PowerDriven)));
            var band = BandAt(report, 0);
            Assert.False(band.Doubt);
            Assert.Null(band.DoubtReason);
            AssertStatuses(band, ColregVesselStatus.PowerDriven, ColregVesselStatus.PowerDriven);
            Assert.Contains(report.Assumptions, a => a.Contains("CollisionRisk") && a.Contains("None"));
            Assert.Equal(new[] { "PowerDriven", "NotUnderCommand", "RestrictedManoeuvrability", "ConstrainedByDraught",
                "Fishing", "Sailing", "Unknown" }, Enum.GetNames(typeof(ColregVesselStatus)));
        }

        [Fact]
        public void Contract_DoubtReasons_UseFixedSnakeCaseNames()
        {
            Assert.Equal("head_on_doubt", ColregDoubtReasons.HeadOnDoubt);
            Assert.Equal("contradictory_views", ColregDoubtReasons.ContradictoryViews);
            Assert.Equal("locked_during_turn", ColregDoubtReasons.LockedDuringTurn);
            Assert.Equal("pending_stable_heading", ColregDoubtReasons.PendingStableHeading);
            Assert.Equal("axis_view", ColregDoubtReasons.AxisView);
        }

        [Theory]
        [InlineData(ColregDangerStage.None, "None")]
        [InlineData(ColregDangerStage.CollisionRisk, "None")]
        [InlineData(ColregDangerStage.CloseQuarters, "CloseQuarters")]
        [InlineData(ColregDangerStage.ImmediateDanger, "ImmediateDanger")]
        public void Contract_DangerStageNames_MapCollisionRiskToNone(ColregDangerStage stage, string expected)
        {
            Assert.Equal(expected, ColregContractNames.DangerStage(stage));
        }

        [Theory]
        [InlineData(RuleCheckStatus.Satisfied, "Complies")]
        [InlineData(RuleCheckStatus.NotSatisfied, "NotComplied")]
        [InlineData(RuleCheckStatus.Partial, "Partial")]
        [InlineData(RuleCheckStatus.NotApplicable, "NotApplicable")]
        [InlineData(RuleCheckStatus.NeedsReview, "NeedsReview")]
        [InlineData(RuleCheckStatus.NotAssessable, "NotAssessable")]
        public void Contract_VerdictNames_PreserveReviewAndEvidenceDistinction(RuleCheckStatus status, string expected)
        {
            Assert.Equal(expected, ColregContractNames.Verdict(status));
        }

        private static ColregAnalysisRequest HeadOnRequest(double duration = 100, bool inSight = true,
            IReadOnlyList<ColregVesselStatusSample> status = null)
        {
            return new ColregAnalysisRequest(Own, Target, Linear(0, 0, 0, 5, duration), Linear(0, 4000, 180, 5, duration),
                visibilityNm: 0.5, vesselsInSight: inSight, vesselStatusSamples: status);
        }

        private static ColregAnalysisRequest OffBow(double bearing, double heading, ColregThresholds thresholds = null, double duration = 1)
        {
            return new ColregAnalysisRequest(Own, Target, Linear(0, 0, 0, 5, duration),
                Linear(2000 * Sin(bearing), 2000 * Cos(bearing), heading, 5, duration), thresholds, vesselsInSight: true);
        }

        private static ColregAnalysisRequest DeferredRequest(bool turnOwn = false, Func<double, double> targetHeading = null,
            int duration = 200, ColregThresholds thresholds = null)
        {
            Func<double, double> offset = t => 20 * (1 - Math.Min(t, 50) / 50);
            var own = GroundTrack(0, 0, 0, 5, t => turnOwn ? offset(t) : 0, duration);
            var target = GroundTrack(0, 7800, 180, 5, targetHeading ?? (t => turnOwn ? 180 : 180 - offset(t)), duration);
            return new ColregAnalysisRequest(Own, Target, own, target, thresholds, vesselsInSight: true);
        }

        private static ColregAnalysisRequest Swap(ColregAnalysisRequest r)
        {
            return new ColregAnalysisRequest(r.TargetVesselId, r.OwnVesselId, r.TargetSamples, r.OwnSamples,
                r.Thresholds, r.Environment, r.VisibilityNm, r.VesselsInSight, r.InNarrowChannel, r.CaseEpochUtc,
                r.InSightSamples, r.ChannelCenterline, r.CaseId, r.EvidenceIds, r.VesselStatusSamples);
        }

        private static ColregAnalysisReport Analyze(ColregAnalysisRequest request)
        {
            var result = new ColregEngine().Analyze(request);
            Assert.True(result.IsSuccess, result.ErrorCode + " " + result.ErrorMessage);
            return result.Value;
        }

        private static ColregVesselStatusSample Status(string vessel, double time, ColregVesselStatus status)
        {
            return new ColregVesselStatusSample(vessel, new SimTime(time), status);
        }

        private static ColregVesselStatusSample[] Statuses(ColregVesselStatus own, ColregVesselStatus target)
        {
            return new[] { Status(Own, 0, own), Status(Target, 0, target) };
        }

        private static IEnumerable<ColregRuleCheck> Checks(ColregAnalysisReport r, ColregRuleId rule, string vessel)
        {
            return r.RuleChecks.Where(c => c.RuleId == rule && c.VesselId == vessel);
        }

        private static bool Overlaps(ColregRuleCheck c, double start, double end)
        {
            return c.StartTime.Seconds < end && c.EndTime.Seconds > start;
        }

        private static void AssertRuleStatuses(ColregAnalysisReport r, string vessel, double start, double end,
            RuleCheckStatus expected, params ColregRuleId[] rules)
        {
            foreach (var rule in rules)
            {
                var checks = Checks(r, rule, vessel).Where(c => Overlaps(c, start, end)).ToArray();
                Assert.NotEmpty(checks); // 防止空集合上的 Assert.All 伪通过。
                Assert.All(checks, c => Assert.Equal(expected, c.Status));
            }
        }

        private static void AssertGeneralChecksRemain(ColregAnalysisReport r, string vessel, double start, double end)
        {
            foreach (var rule in new[] { ColregRuleId.R5, ColregRuleId.R7, ColregRuleId.R8 })
                Assert.Contains(Checks(r, rule, vessel), c => Overlaps(c, start, end) && c.Status != RuleCheckStatus.NotApplicable);
        }

        private static ColregTimeBand BandAt(ColregAnalysisReport r, double time)
        {
            // 左闭右开；共享边界属于后带，报告终点亦可查询。
            var band = r.TimeBands.LastOrDefault(b => b.StartTime.Seconds <= time && time <= b.EndTime.Seconds);
            Assert.NotNull(band);
            return band;
        }

        private static TrafficRole RoleOf(ColregTimeBand band, ColregAnalysisRequest r, string vessel)
        {
            return r.OwnVesselId == vessel ? band.OwnRole : band.TargetRole;
        }

        private static void AssertStatuses(ColregTimeBand band, ColregVesselStatus own, ColregVesselStatus target)
        {
            Assert.NotNull(band.VesselStatus);
            Assert.Equal(2, band.VesselStatus.Count);
            Assert.True(band.VesselStatus.ContainsKey(Own));
            Assert.True(band.VesselStatus.ContainsKey(Target));
            Assert.Equal(own, band.VesselStatus[Own]);
            Assert.Equal(target, band.VesselStatus[Target]);
        }

        private static void AssertPending(ColregTimeBand band)
        {
            Assert.Equal(EncounterSituation.Undetermined, band.Situation);
            Assert.True(band.Doubt);
            Assert.Equal(ColregDoubtReasons.PendingStableHeading, band.DoubtReason);
            Assert.Equal(TrafficRole.Undetermined, band.OwnRole);
            Assert.Equal(TrafficRole.Undetermined, band.TargetRole);
            Assert.Null(band.GiveWayVesselId);
            Assert.Null(band.StandOnVesselId);
        }

        private static string[] CheckStatuses(ColregAnalysisReport report)
        {
            return report.RuleChecks.Select(c => string.Join("|", c.RuleId, c.Clause, c.VesselId,
                c.StartTime.Seconds.ToString("R", CultureInfo.InvariantCulture),
                c.EndTime.Seconds.ToString("R", CultureInfo.InvariantCulture), c.Status))
                .OrderBy(c => c, StringComparer.Ordinal).ToArray();
        }

        private static TrackSample[] Linear(double east, double north, double course, double speed, double duration)
        {
            return new[] { Sample(0, east, north, course, speed, course),
                Sample(duration, east + speed * Sin(course) * duration, north + speed * Cos(course) * duration, course, speed, course) };
        }

        private static TrackSample[] GroundTrack(double east, double north, double course, double speed,
            Func<double, double> heading, int duration)
        {
            var samples = new List<TrackSample>();
            for (int time = 0; time <= duration; time += 10)
                samples.Add(Sample(time, east + speed * Sin(course) * time, north + speed * Cos(course) * time,
                    course, speed, heading(time)));
            return samples.ToArray();
        }

        private static TrackSample[] Integrate(double east, double north, Func<double, double> heading, double speed, int duration)
        {
            var samples = new List<TrackSample>();
            for (int time = 0; time <= duration; time++)
            {
                if (time % 10 == 0 || time == duration)
                    samples.Add(Sample(time, east, north, heading(time), speed, heading(time)));
                east += speed * Sin(heading(time + 0.5));
                north += speed * Cos(heading(time + 0.5));
            }
            return samples.ToArray();
        }

        private static TrackSample Sample(double time, double east, double north, double course, double speed, double heading)
        {
            return new TrackSample(new SimTime(time), new GeoCoord(0, 0), new EnuPosition(east, north),
                new Double2(speed * Sin(course), speed * Cos(course)), (float)speed, (float)Normalize(course),
                (float)Normalize(heading), 0, SampleProvenance.Presumed, TimeQuality.Estimated, false);
        }

        private static double Normalize(double angle) { return (angle % 360 + 360) % 360; }
        private static double Sin(double angle) { double v = Math.Sin(angle * Math.PI / 180); return Math.Abs(v) < 1e-12 ? 0 : v; }
        private static double Cos(double angle) { double v = Math.Cos(angle * Math.PI / 180); return Math.Abs(v) < 1e-12 ? 0 : v; }
    }
}

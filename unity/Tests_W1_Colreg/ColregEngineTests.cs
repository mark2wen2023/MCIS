using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Colreg;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Models;
using Xunit;

namespace Mcis.Tests.W1
{
    /// <summary>全部航迹均为合成虚构数据，坐标采用局部 ENU 米。</summary>
    public sealed class ColregEngineTests
    {
        private const string Own = "虚构甲船";
        private const string Target = "虚构乙船";

        [Fact]
        public void ExactHeadOn_HasBothStarboardObligationsAndNoStandOn()
        {
            var report = HeadOn();
            var band = report.TimeBands.First();
            Assert.Equal(EncounterSituation.HeadOn, band.Situation);
            Assert.Equal(TrafficRole.BothActionRequired, band.OwnRole);
            Assert.Equal(TrafficRole.BothActionRequired, band.TargetRole);
            Assert.Contains(ColregRuleId.R14, band.ApplicableRules);
            foreach (var vessel in new[] { Own, Target })
            {
                var check = report.RuleChecks.First(c => c.RuleId == ColregRuleId.R14 && c.VesselId == vessel);
                Assert.False(string.IsNullOrWhiteSpace(check.ExpectedAction));
                Assert.Contains("右", check.ExpectedAction);
                Assert.Equal(RuleCheckStatus.NotSatisfied, check.Status);
                Assert.Equal(180.0, check.Evidence.HeadingDifferenceDeg, 6);
            }
        }

        [Theory]
        [InlineData(-6.0)]
        [InlineData(6.0)]
        public void HeadOnHalfAngle_IncludesSixDegreeBoundary(double offset)
        {
            Assert.Equal(EncounterSituation.HeadOn, HeadOn(offset).TimeBands.First().Situation);
        }

        [Theory]
        [InlineData(-6.1)]
        [InlineData(6.1)]
        [InlineData(7.0)]
        public void HeadOnHalfAngle_ExcludesAnglesBeyondBoundary(double offset)
        {
            Assert.Equal(EncounterSituation.Crossing, HeadOn(offset).TimeBands.First().Situation);
        }

        [Theory]
        [InlineData(112.5)]
        [InlineData(112.51)]
        [InlineData(247.49)]
        [InlineData(247.5)]
        public void OvertakingSector_IsClosedAt112Point5And247Point5(double bearing)
        {
            var r = Analyze(Linear(0, 0, 0, 5), Linear(1000 * Sin(bearing), 1000 * Cos(bearing), 0, 10));
            Assert.Equal(EncounterSituation.Overtaking, r.TimeBands.First().Situation);
            Assert.Equal(TrafficRole.StandOn, r.TimeBands.First().OwnRole);
            Assert.Equal(TrafficRole.GiveWay, r.TimeBands.First().TargetRole);
            Assert.Contains(ColregRuleId.R13, r.TimeBands.First().ApplicableRules);
        }

        [Theory]
        [InlineData(112.49)]
        [InlineData(247.51)]
        public void OutsideOvertakingSector_IsCrossing(double bearing)
        {
            var r = Analyze(Linear(0, 0, 0, 5), Linear(1000 * Sin(bearing), 1000 * Cos(bearing), 0, 10));
            Assert.Equal(EncounterSituation.Crossing, r.TimeBands.First().Situation);
        }

        [Theory]
        [InlineData(1000.0, 270.0, TrafficRole.GiveWay, TrafficRole.StandOn)]
        [InlineData(-1000.0, 90.0, TrafficRole.StandOn, TrafficRole.GiveWay)]
        public void Crossing_StarboardVesselDeterminesRoles(double east, double heading, TrafficRole own, TrafficRole target)
        {
            var r = Analyze(Linear(0, 0, 0, 5), Linear(east, 1000, heading, 5));
            Assert.Equal(EncounterSituation.Crossing, r.TimeBands.First().Situation);
            Assert.Equal(own, r.TimeBands.First().OwnRole);
            Assert.Equal(target, r.TimeBands.First().TargetRole);
            Assert.Contains(ColregRuleId.R15, r.TimeBands.First().ApplicableRules);
        }

        [Theory]
        [InlineData(1.9, true, EncounterSituation.HeadOn)]
        [InlineData(8.0, false, EncounterSituation.RestrictedVisibility)]
        public void RestrictedVisibilityOrExplicitNotInSight_TakesPrecedence(double visibility, bool inSight, EncounterSituation expected)
        {
            // D03 裁定：显式互见优先于低能见度；显式未互见仍适用 R19。
            var r = Analyze(Linear(0, 0, 0, 5), Linear(0, 4000, 180, 5), visibility: visibility, inSight: inSight);
            var band = r.TimeBands.First();
            Assert.Equal(expected, band.Situation);
            Assert.Equal(TrafficRole.BothActionRequired, band.OwnRole);
            Assert.Equal(TrafficRole.BothActionRequired, band.TargetRole);
            if (inSight)
            {
                Assert.Contains(ColregRuleId.R14, band.ApplicableRules);
                Assert.DoesNotContain(ColregRuleId.R19, band.ApplicableRules);
                Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R14 && c.Status != RuleCheckStatus.NotApplicable);
                return;
            }
            Assert.Contains(ColregRuleId.R19, band.ApplicableRules);
            Assert.DoesNotContain(ColregRuleId.R14, band.ApplicableRules);
            Assert.DoesNotContain(ColregRuleId.R15, band.ApplicableRules);
            Assert.All(r.RuleChecks.Where(c => c.RuleId == ColregRuleId.R14 || c.RuleId == ColregRuleId.R15 || c.RuleId == ColregRuleId.R13), c => Assert.Equal(RuleCheckStatus.NotApplicable, c.Status));
        }

        [Fact]
        public void RestrictedVisibility_PortTurnForVesselAhead_FailsR19()
        {
            var own = new[] { Sample(0, 0, 0, 0, 5), Sample(10, -4.36, 49.8, 350, 5) };
            // D03：低能见度不再覆盖显式互见；本用例明确指定未互见以核查 R19。
            var r = Analyze(own, Linear(0, 4000, 180, 5), visibility: 1, inSight: false);
            Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R19 && c.VesselId == Own && c.Status == RuleCheckStatus.NotSatisfied && c.ActualAction.Turn == TurnDirection.Port);
        }

        [Fact]
        public void HeadOn_PortTurnFailsThatVesselsR14()
        {
            var own = new[] { Sample(0, 0, 0, 0, 5), Sample(10, -4.36, 49.8, 350, 5) };
            var r = Analyze(own, Linear(0, 4000, 180, 5));
            Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R14 && c.VesselId == Own && c.Status == RuleCheckStatus.NotSatisfied && c.ActualAction.Turn == TurnDirection.Port);
        }

        [Fact]
        public void GiveWay_EarlySubstantialSafeStarboardTurn_SatisfiesR16AndR8()
        {
            var own = new[] { Sample(0, 0, 0, 0, 5), Sample(10, 19.134, 46.194, 45, 5) };
            var r = Analyze(own, Linear(3000, 3000, 270, 5));
            foreach (var rule in new[] { ColregRuleId.R16, ColregRuleId.R8 })
                Assert.Contains(r.RuleChecks, c => c.RuleId == rule && c.VesselId == Own && c.Status == RuleCheckStatus.Satisfied && c.ActualAction.Turn == TurnDirection.Starboard && c.Evidence.HeadingChangeDeg >= 10);
            Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R17 && c.VesselId == Target && c.Status == RuleCheckStatus.Satisfied);
        }

        [Fact]
        public void RestrictedVisibilityBecomesClear_ProducesTimeBandsAtTransition()
        {
            var environment = new[] { Environment(0, 1), Environment(20, 8) };
            // D03/D04：留空互见标志，由环境和距离推导互见转换。
            var r = Analyze(Linear(0, 0, 0, 5, 40), Linear(0, 4000, 180, 5, 40), inSight: null, environment: environment);
            Assert.Equal(2, r.TimeBands.Count);
            Assert.Equal(EncounterSituation.RestrictedVisibility, r.TimeBands[0].Situation);
            Assert.Equal(20, r.TimeBands[0].EndTime.Seconds);
            Assert.Equal(EncounterSituation.HeadOn, r.TimeBands[1].Situation);
            Assert.Equal(20, r.TimeBands[1].StartTime.Seconds);
        }

        [Fact]
        public void HeadOnThresholdEightDegreeOffset_ChangesWithConfiguration()
        {
            Assert.Equal(EncounterSituation.Crossing, HeadOn(8).TimeBands.First().Situation);
            var thresholds = new ColregThresholds(headOnHalfAngleDeg: 10);
            var r = HeadOn(8, thresholds);
            Assert.Equal(EncounterSituation.HeadOn, r.TimeBands.First().Situation);
            Assert.Same(thresholds, r.Thresholds);
            Assert.Equal(10, r.Thresholds.HeadOnHalfAngleDeg);
        }

        [Fact]
        public void Report_HasExactDisclaimerAndEveryCoreRuleAndActionPairing()
        {
            var r = HeadOn();
            Assert.Equal("仅作安全调查技术分析，不作责任认定。", r.Disclaimer);
            foreach (var rule in new[] { ColregRuleId.R8, ColregRuleId.R13, ColregRuleId.R14, ColregRuleId.R15, ColregRuleId.R16, ColregRuleId.R17, ColregRuleId.R19 })
                Assert.Contains(r.RuleChecks, c => c.RuleId == rule);
            Assert.NotEmpty(r.ActionComparisons);
            Assert.All(r.ActionComparisons, c =>
            {
                Assert.False(string.IsNullOrWhiteSpace(c.ExpectedAction));
                Assert.True(c.EndTime >= c.StartTime);
                Assert.Contains(r.RuleChecks, x => x.RuleId == c.RuleId && x.VesselId == c.VesselId);
            });
        }

        [Fact]
        public void NarrowChannel_IncludesR9AndExplicitUnavailableGeometry()
        {
            var r = Analyze(Linear(0, 0, 0, 5), Linear(0, 4000, 180, 5), narrow: true);
            Assert.Contains(ColregRuleId.R9, r.TimeBands.First().ApplicableRules);
            var checks = r.RuleChecks.Where(c => c.RuleId == ColregRuleId.R9).ToList();
            Assert.NotEmpty(checks);
            Assert.All(checks, c =>
            {
                // A6：已标狭水道但缺少航道几何，应表达不能评估，而非不适用。
                Assert.Equal(RuleCheckStatus.NotAssessable, c.Status);
                Assert.False(string.IsNullOrWhiteSpace(c.Clause));
            });
        }

        [Fact]
        public void FarDivergingTracks_AreNotEncounterWithCollisionRisk()
        {
            var r = Analyze(Linear(0, 0, 180, 5), Linear(0, 4000, 0, 5));
            Assert.Equal(EncounterSituation.NoCollisionRisk, r.TimeBands.First().Situation);
            Assert.Equal(TrafficRole.None, r.TimeBands.First().OwnRole);
            Assert.Equal(TrafficRole.None, r.TimeBands.First().TargetRole);
        }

        [Fact]
        public void EquivalentVelocities_AreDegenerateWithoutFalseCollisionRisk()
        {
            var r = Analyze(Linear(0, 0, 0, 5), Linear(0, 100, 0, 5));
            Assert.Equal(EncounterSituation.NoCollisionRisk, r.TimeBands.First().Situation);
        }

        [Fact]
        public void EvidenceDcpaAndTcpa_ReuseExistingCpaCalculator()
        {
            var own = Linear(0, 0, 0, 5);
            var target = Linear(1000, 1000, 270, 5);
            var expected = CpaCalculator.CalculateFromSamples(own[0], target[0]);
            var r = Analyze(own, target);
            var evidence = r.RuleChecks.First(c => c.RuleId == ColregRuleId.R15 && c.VesselId == Own).Evidence;
            Assert.Equal(expected.DcpaM, evidence.DcpaM, 6);
            Assert.Equal(expected.TcpaSec, evidence.TcpaSeconds, 6);
            Assert.Equal(45, evidence.RelativeBearingDeg, 6);
        }

        [Fact]
        public void CogIsUsedWhenHeadingUnavailableOrExplicitlyFromCog()
        {
            var own = new[] { Sample(0, 0, 0, 0, 5, hdg: float.NaN), Sample(10, 0, 50, 0, 5, hdg: float.NaN) };
            Assert.Equal(EncounterSituation.HeadOn, Analyze(own, Linear(0, 4000, 180, 5)).TimeBands.First().Situation);
            own = new[] { Sample(0, 0, 0, 0, 5, hdg: 90, fromCog: true), Sample(10, 0, 50, 0, 5, hdg: 90, fromCog: true) };
            Assert.Equal(EncounterSituation.HeadOn, Analyze(own, Linear(0, 4000, 180, 5)).TimeBands.First().Situation);
        }

        [Fact]
        public void HeadingWraparound_RightTurnFrom355To15_IsTwentyDegrees()
        {
            var own = new[] { Sample(0, 0, 0, 355, 5), Sample(10, 4.36, 49.8, 15, 5) };
            var target = Linear(-348.623, 3984.779, 175, 5);
            var r = Analyze(own, target);
            Assert.Contains(r.ActionComparisons, c => c.VesselId == Own && c.ActualAction.Turn == TurnDirection.Starboard && Math.Abs(c.ActualAction.HeadingChangeDeg - 20) < 1e-6);
        }

        [Fact]
        public void CollinearOvertaking_RemainsUntilPassedAndClear()
        {
            var own = Linear(0, 0, 0, 5, 400);
            var target = Linear(100, -500, 0, 10, 400);
            var r = Analyze(own, target);
            Assert.Equal(EncounterSituation.Overtaking, r.TimeBands.First().Situation);
            Assert.Contains(r.TimeBands, b => b.Situation == EncounterSituation.Overtaking && b.EndTime.Seconds > 100);
            Assert.Equal(EncounterSituation.NoCollisionRisk, r.TimeBands.Last().Situation);
            Assert.All(r.TimeBands.Where(b => b.Situation == EncounterSituation.Overtaking), b => Assert.Equal(TrafficRole.GiveWay, b.TargetRole));
        }

        [Fact]
        public void EmptyTracks_ReturnFailedResult()
        {
            var result = new ColregEngine().Analyze(new ColregAnalysisRequest(Own, Target, Array.Empty<TrackSample>(), Linear(0, 4000, 180, 5)));
            Assert.False(result.IsSuccess);
            Assert.False(string.IsNullOrWhiteSpace(result.ErrorCode));
        }

        [Fact]
        public void UnsortedTracks_ReturnFailedResult()
        {
            var own = Linear(0, 0, 0, 5).Reverse().ToArray();
            var result = new ColregEngine().Analyze(new ColregAnalysisRequest(Own, Target, own, Linear(0, 4000, 180, 5)));
            Assert.False(result.IsSuccess);
        }

        [Fact]
        public void NonOverlappingTracks_ReturnFailedResult()
        {
            var target = new[] { Sample(100, 0, 4000, 180, 5), Sample(110, 0, 3950, 180, 5) };
            var result = new ColregEngine().Analyze(new ColregAnalysisRequest(Own, Target, Linear(0, 0, 0, 5), target));
            Assert.False(result.IsSuccess);
        }

        [Fact]
        public void CaseEpochUtc_IsRetainedForDisplay()
        {
            var epoch = new DateTimeOffset(2026, 1, 1, 6, 15, 0, TimeSpan.Zero);
            var result = new ColregEngine().Analyze(new ColregAnalysisRequest(Own, Target, Linear(0, 0, 0, 5), Linear(0, 4000, 180, 5), caseEpochUtc: epoch));
            Assert.True(result.IsSuccess, result.ErrorMessage);
            Assert.Equal(epoch, result.Value.CaseEpochUtc);
        }

        [Theory]
        [InlineData(135.0, 20.0, TurnDirection.Starboard)]
        [InlineData(225.0, 340.0, TurnDirection.Port)]
        public void RestrictedVisibility_TurnTowardVesselAbaftBeam_FailsR19(double bearing, double ownFinalHeading, TurnDirection turn)
        {
            var own = new[] { Sample(0, 0, 0, 0, 5), Sample(10, 25 * Sin(ownFinalHeading), 25 + 25 * Cos(ownFinalHeading), ownFinalHeading, 5) };
            var target = Linear(500 * Sin(bearing), 500 * Cos(bearing), 0, 10);
            // D03/D04：即使距离在能见范围内，显式未互见仍适用 R19。
            var r = Analyze(own, target, visibility: 1, inSight: false);
            Assert.Equal(EncounterSituation.RestrictedVisibility, r.TimeBands.First().Situation);
            Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R19 && c.VesselId == Own && c.Status == RuleCheckStatus.NotSatisfied && c.ActualAction.Turn == turn);
        }

        [Fact]
        public void EarlySubstantialTurn_WithInsufficientPassingDistance_DoesNotSatisfyR8()
        {
            var own = new[] { Sample(0, 0, 0, 0, 5), Sample(10, 4.358, 49.8, 10, 5) };
            var r = Analyze(own, Linear(1000, 1000, 270, 5));
            var checks = r.RuleChecks.Where(c => c.RuleId == ColregRuleId.R8 && c.VesselId == Own).ToList();
            Assert.NotEmpty(checks);
            Assert.DoesNotContain(checks, c => c.Status == RuleCheckStatus.Satisfied);
            Assert.Contains(checks, c => c.ActualAction.Turn == TurnDirection.Starboard && c.Evidence.HeadingChangeDeg >= 10);
        }

        [Fact]
        public void StandOnMayIntervene_WhenGiveWayHasNotActedAndTimeIsShort()
        {
            var own = new[] { Sample(0, 0, 0, 0, 5), Sample(10, 19.134, 46.194, 45, 5) };
            var r = Analyze(own, Linear(-600, 600, 90, 5), new ColregThresholds(safePassingDcpaNm: 0.1));
            Assert.Equal(TrafficRole.StandOn, r.TimeBands.First().OwnRole);
            Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R17 && c.VesselId == Own && c.Status == RuleCheckStatus.Satisfied && c.ActualAction.Turn == TurnDirection.Starboard);
        }

        [Fact]
        public void StandOnMustAct_InConfiguredEmergencyWindow()
        {
            var r = Analyze(Linear(0, 0, 0, 5), Linear(-200, 200, 90, 5));
            Assert.Equal(TrafficRole.StandOn, r.TimeBands.First().OwnRole);
            Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R17 && c.VesselId == Own && c.Status == RuleCheckStatus.NotSatisfied);
        }

        [Fact]
        public void StandOnPrematureCourseChange_DoesNotSatisfyR17()
        {
            var own = new[] { Sample(0, 0, 0, 0, 5), Sample(10, 19.134, 46.194, 45, 5) };
            var r = Analyze(own, Linear(-3000, 3000, 90, 5));
            Assert.Equal(TrafficRole.StandOn, r.TimeBands.First().OwnRole);
            Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R17 && c.VesselId == Own && c.Status == RuleCheckStatus.NotSatisfied);
        }

        [Fact]
        public void StandOnCourseExcursionThenReturn_IsNotMaintainingHeading()
        {
            var own = new[] { Sample(0, 0, 0, 0, 5), Sample(10, 8.55, 48.49, 20, 5), Sample(20, 17.10, 96.98, 0, 5) };
            var r = Analyze(own, Linear(-3000, 3000, 90, 5, 20));
            Assert.Equal(TrafficRole.StandOn, r.TimeBands.First().OwnRole);
            Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R17 && c.VesselId == Own && c.Status == RuleCheckStatus.NotSatisfied);
        }

        [Fact]
        public void ConfiguredOvertakingBoundary_Changes115DegreeClassification()
        {
            var target = Linear(1000 * Sin(115), 1000 * Cos(115), 0, 10);
            Assert.Equal(EncounterSituation.Overtaking, Analyze(Linear(0, 0, 0, 5), target).TimeBands.First().Situation);
            var r = Analyze(Linear(0, 0, 0, 5), target, new ColregThresholds(overtakingAbaftBeamAngleDeg: 30));
            Assert.Equal(EncounterSituation.Crossing, r.TimeBands.First().Situation);
        }

        [Fact]
        public void ConfiguredRestrictedVisibilityThreshold_IsApplied()
        {
            var own = Linear(0, 0, 0, 5);
            var target = Linear(0, 4000, 180, 5);
            // D04：距离约 2.16 nm；使用相同 2 nm 能见度隔离可配环境阈值的影响。
            Assert.Equal(EncounterSituation.HeadOn, Analyze(own, target, visibility: 2, inSight: null).TimeBands.First().Situation);
            Assert.Equal(EncounterSituation.RestrictedVisibility, Analyze(own, target, new ColregThresholds(restrictedVisibilityNm: 3), visibility: 2, inSight: null).TimeBands.First().Situation);
            // D04：即使属于能见度不良，距离已在 2.5 nm 能见范围内仍应互见。
            Assert.Equal(EncounterSituation.HeadOn, Analyze(own, target, new ColregThresholds(restrictedVisibilityNm: 3), visibility: 2.5, inSight: null).TimeBands.First().Situation);
        }

        [Fact]
        public void LateSubstantialSafeTurn_DoesNotSatisfyEarlyActionRules()
        {
            var own = new[] { Sample(0, 0, 0, 0, 5), Sample(10, 19.134, 46.194, 45, 5) };
            var r = Analyze(own, Linear(300, 300, 270, 5), new ColregThresholds(safePassingDcpaNm: 0.05));
            foreach (var rule in new[] { ColregRuleId.R8, ColregRuleId.R16 })
            {
                var checks = r.RuleChecks.Where(c => c.RuleId == rule && c.VesselId == Own).ToList();
                Assert.NotEmpty(checks);
                Assert.DoesNotContain(checks, c => c.Status == RuleCheckStatus.Satisfied);
            }
        }

        [Fact]
        public void OvertakingPassingThroughOtherVessel_CannotBeSatisfiedBySafeFinalSeparation()
        {
            // 虚构追越：前100秒匀加速10→11m/s，随后保持11m/s；675秒两船中心重合。
            var own = new[]
            {
                Sample(0, 0, -4000, 0, 10),
                Sample(100, 0, -2950, 0, 11),
                Sample(675, 0, 3375, 0, 11),
                Sample(900, 0, 5850, 0, 11)
            };
            // A5：默认危险前瞻缩为 720 s；显式放宽以保留原用例从 t=0 开始追越的前提。
            var r = Analyze(own, Linear(0, 0, 0, 5, 900), new ColregThresholds(collisionRiskTcpaSeconds: 900));
            var overtaking = r.TimeBands.First();
            Assert.Equal(EncounterSituation.Overtaking, overtaking.Situation);
            Assert.Equal(TrafficRole.GiveWay, overtaking.OwnRole);
            Assert.True(overtaking.EndTime.Seconds > 675);
            Assert.Equal(EncounterSituation.NoCollisionRisk, r.TimeBands.Last().Situation);
            foreach (var rule in new[] { ColregRuleId.R8, ColregRuleId.R16, ColregRuleId.R13 })
            {
                var checks = r.RuleChecks.Where(c => c.RuleId == rule && c.VesselId == Own && c.StartTime < overtaking.EndTime).ToList();
                Assert.NotEmpty(checks);
                Assert.DoesNotContain(checks, c => c.Status == RuleCheckStatus.Satisfied);
            }
        }

        [Fact]
        public void StandOnLongEncounter_ReevaluatesInterventionWhenRemainingTcpaBecomesShort()
        {
            // 虚构交叉：初始TCPA400秒，保向250秒后剩余150秒，此时右转45度。
            var own = new[]
            {
                Sample(0, 0, 0, 0, 5),
                Sample(250, 0, 1250, 0, 5),
                Sample(260, 19.134, 1296.194, 45, 5)
            };
            var r = Analyze(own, Linear(-2000, 2000, 90, 5, 260), new ColregThresholds(safePassingDcpaNm: 0.1));
            Assert.Equal(TrafficRole.StandOn, r.TimeBands.First().OwnRole);
            var checks = r.RuleChecks.Where(c => c.RuleId == ColregRuleId.R17 && c.VesselId == Own).ToList();
            Assert.Contains(checks, c => c.Status == RuleCheckStatus.Satisfied && c.EndTime.Seconds <= 250 && c.ActualAction.Turn == TurnDirection.None);
            Assert.Contains(checks, c => c.Status == RuleCheckStatus.Satisfied && c.StartTime.Seconds >= 220 && c.EndTime.Seconds >= 260 && c.ActualAction.Turn == TurnDirection.Starboard);
        }

        [Fact]
        public void RestrictedVisibilityWithoutCollisionRisk_DoesNotRequireR8AvoidanceAction()
        {
            // D03：本场景明确未互见；规格 8 要求无危险区段除 R9 外均不适用。
            var r = Analyze(Linear(0, 0, 0, 5), Linear(0, 4000, 0, 5), visibility: 1, inSight: false);
            Assert.Equal(EncounterSituation.RestrictedVisibility, r.TimeBands.First().Situation);
            var checks = r.RuleChecks.Where(c => c.RuleId == ColregRuleId.R8).ToList();
            Assert.NotEmpty(checks);
            Assert.All(checks, c => Assert.Equal(RuleCheckStatus.NotApplicable, c.Status));
            Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R19 && c.Clause == "R19(b)" && c.Status == RuleCheckStatus.NotApplicable);
        }

        [Fact]
        public void DirectionalTurnExcursion_ReachingTenDegreesHasSubstantialActionTime()
        {
            // 虚构航向0→352(-8)→4(+12)，第二段单向右转超过10度，净变化仅4度。
            var own = new[]
            {
                Sample(0, 0, 0, 0, 5),
                Sample(10, -3.479, 49.757, 352, 5),
                Sample(20, -5.214, 99.391, 4, 5)
            };
            // A5：本用例专测折返后的单向转幅和动作时刻，显式保留 10° 配置；默认已改 30°。
            var r = Analyze(own, Linear(0, 4000, 180, 5, 20), new ColregThresholds(substantialTurnDeg: 10), visibility: 1, inSight: false);
            Assert.Single(r.TimeBands);
            var action = r.ActionComparisons.First(c => c.VesselId == Own).ActualAction;
            Assert.Equal(4, action.HeadingChangeDeg, 6);
            Assert.Equal(12, action.MaxStarboardTurnDeg, 6);
            Assert.True(action.FirstSubstantialActionTime.HasValue);
            Assert.InRange(action.FirstSubstantialActionTime.Value.Seconds, 10.000001, 20);
        }

        [Fact]
        public void ClosingVesselInOvertakingSector_HasStableRolesIndependentOfIds()
        {
            // 虚构A向北5m/s，B在东北侧向东2m/s；A处于B相对135度且两船正在接近。
            // 沿B船首方向的相对速度投影为负，不能据此漏掉追越优先判据。
            var own = Linear(0, 0, 0, 5);
            var target = Linear(500, 500, 90, 2);
            var pairs = new[] { new[] { "虚构A", "虚构B" }, new[] { "虚构Z", "虚构A" } };
            foreach (var ids in pairs)
            {
                var result = new ColregEngine().Analyze(new ColregAnalysisRequest(ids[0], ids[1], own, target));
                Assert.True(result.IsSuccess, result.ErrorMessage);
                var band = result.Value.TimeBands.First();
                Assert.Equal(EncounterSituation.Overtaking, band.Situation);
                Assert.Equal(TrafficRole.GiveWay, band.OwnRole);
                Assert.Equal(TrafficRole.StandOn, band.TargetRole);
            }
        }

        [Fact]
        public void OvertakingCollisionBetweenObservationTimes_IsDetectedBySegmentCpa()
        {
            // 虚构A在675秒穿过B；源样本和10秒网格均不含675秒。
            // 670/680秒最近采样净距为30米；1.852米门限要求核查连续观测段，不能只看采样点。
            var own = new[]
            {
                Sample(0, 0, -4000, 0, 10),
                Sample(100, 0, -2950, 0, 11),
                Sample(900, 0, 5850, 0, 11)
            };
            // A5：显式前瞻 900 s，继续检验追越期间采样间的碰撞，避免默认 720 s 改变首带前提。
            var r = Analyze(own, Linear(0, 0, 0, 5, 900), new ColregThresholds(safePassingDcpaNm: 0.001, collisionRiskTcpaSeconds: 900));
            var overtaking = r.TimeBands.First();
            Assert.Equal(EncounterSituation.Overtaking, overtaking.Situation);
            Assert.True(overtaking.EndTime.Seconds > 675);
            foreach (var rule in new[] { ColregRuleId.R8, ColregRuleId.R16, ColregRuleId.R13 })
            {
                var checks = r.RuleChecks.Where(c => c.RuleId == rule && c.VesselId == Own && c.StartTime < overtaking.EndTime).ToList();
                Assert.NotEmpty(checks);
                Assert.DoesNotContain(checks, c => c.Status == RuleCheckStatus.Satisfied);
            }
        }

        [Fact]
        public void RestrictedVisibilityBand_ReevaluatesR8WhenCollisionRiskAppearsLater()
        {
            // 虚构目标先同速向北，10秒时转为向南；能见度与会遇分类全程保持不变。
            var target = new[]
            {
                Sample(0, 100, 500, 0, 5),
                Sample(10, 100, 550, 180, 5),
                Sample(20, 100, 500, 180, 5)
            };
            // D03/D04：显式未互见，以保持全程 R19 时间带并单独核查危险出现后的 R8。
            var r = Analyze(Linear(0, 0, 0, 5, 20), target, visibility: 1, inSight: false);
            Assert.Single(r.TimeBands);
            Assert.Equal(EncounterSituation.RestrictedVisibility, r.TimeBands[0].Situation);
            foreach (var vessel in new[] { Own, Target })
                Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R8 && c.VesselId == vessel && c.StartTime.Seconds >= 10 && c.Status != RuleCheckStatus.NotApplicable);
        }

        [Fact]
        public void ValidHeadingAndEnuVelocity_DoNotRequireAvailableCog()
        {
            // 虚构航迹已提供有效船首向与ENU速度；COG不可用不能妨碍船首向优先的对遇分析。
            var own = new[]
            {
                new TrackSample(new SimTime(0), new GeoCoord(0, 0), new EnuPosition(0, 0), new Double2(0, 5),
                    5, float.NaN, 0, 0, SampleProvenance.Presumed, TimeQuality.Estimated, false),
                new TrackSample(new SimTime(10), new GeoCoord(0, 0), new EnuPosition(0, 50), new Double2(0, 5),
                    5, float.NaN, 0, 0, SampleProvenance.Presumed, TimeQuality.Estimated, false)
            };
            var result = new ColregEngine().Analyze(new ColregAnalysisRequest(Own, Target, own, Linear(0, 4000, 180, 5)));
            Assert.True(result.IsSuccess, result.ErrorMessage);
            Assert.Equal(EncounterSituation.HeadOn, result.Value.TimeBands.First().Situation);
        }

        [Fact]
        public void ObliqueOvertaking_IsReleasedAfterPassingCpaAndSeparatingClear()
        {
            // 虚构斜向追越：A在B的船尾扇区接近，1000秒时已过CPA且相距数千米。
            var r = Analyze(Linear(0, 0, 0, 5, 1000), Linear(500, 500, 90, 2, 1000));
            Assert.Equal(EncounterSituation.Overtaking, r.TimeBands.First().Situation);
            Assert.Equal(TrafficRole.GiveWay, r.TimeBands.First().OwnRole);
            Assert.Equal(EncounterSituation.NoCollisionRisk, r.TimeBands.Last().Situation);
            Assert.True(r.TimeBands.First().EndTime < r.TimeBands.Last().EndTime);
        }

        [Fact]
        public void StandOnContinuousTurnAcrossEmergencyBoundary_DoesNotRequireAnotherTenDegreeTurn()
        {
            // 虚构A首10秒沿转弧右转10度并由5加至6m/s，再保持6m/s续转5度。
            // ENU按速度积分：TCPA70→58.358→50.483秒，终点DCPA109.247米。
            var own = new[]
            {
                Sample(0, 0, 0, 0, 5),
                Sample(10, 4.932264319154752, 54.70852571529193, 10, 6),
                Sample(20, 17.91452084288903, 113.26770061362254, 15, 6)
            };
            // A5：显式保留旧 10°/1 m/s 代理，原用例只核查连续行动跨 R17 阶段边界。
            var r = Analyze(own, Linear(-350, 350, 90, 5, 20), new ColregThresholds(safePassingDcpaNm: 0.01,
                substantialTurnDeg: 10, substantialSpeedChangeMps: 1));
            Assert.Equal(TrafficRole.StandOn, r.TimeBands.First().OwnRole);
            Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R17 && c.VesselId == Own && c.Clause == "R17(b)" &&
                c.StartTime.Seconds >= 10 && c.EndTime.Seconds >= 20 && c.Status == RuleCheckStatus.Partial &&
                Math.Abs(c.ActualAction.HeadingChangeDeg - 5) < 1e-6);
        }

        [Fact]
        public void CrossingRolesForVesselOnStarboard_DoNotDependOnVesselIds()
        {
            // 虚构A北向、B南向，双方均在相对45度，超过对遇前方15度半角。
            // W1.1 D11 复测裁定：双方同侧视角矛盾，角色须 Undetermined，不能按本船视角分配让路船。
            var own = Linear(0, 0, 0, 5);
            var target = Linear(500, 500, 180, 5);
            var pairs = new[] { new[] { "虚构A", "虚构B" }, new[] { "虚构Z", "虚构A" } };
            foreach (var ids in pairs)
            {
                var result = new ColregEngine().Analyze(new ColregAnalysisRequest(ids[0], ids[1], own, target));
                Assert.True(result.IsSuccess, result.ErrorMessage);
                var band = result.Value.TimeBands.First();
                Assert.Equal(EncounterSituation.Crossing, band.Situation);
                Assert.Equal(TrafficRole.Undetermined, band.OwnRole);
                Assert.Equal(TrafficRole.Undetermined, band.TargetRole);
                Assert.Null(band.GiveWayVesselId);
                Assert.Null(band.StandOnVesselId);
            }
        }

        private static ColregAnalysisReport HeadOn(double offset = 0, ColregThresholds thresholds = null)
        {
            return Analyze(Linear(0, 0, 0, 5), Linear(0, 4000, 180 + offset, 5), thresholds);
        }

        private static ColregAnalysisReport Analyze(IReadOnlyList<TrackSample> own, IReadOnlyList<TrackSample> target, ColregThresholds thresholds = null, double? visibility = 8, bool? inSight = true, bool narrow = false, IReadOnlyList<EnvironmentState> environment = null)
        {
            var result = new ColregEngine().Analyze(new ColregAnalysisRequest(Own, Target, own, target, thresholds, environment, visibility, inSight, narrow));
            Assert.True(result.IsSuccess, result.ErrorMessage);
            return result.Value;
        }

        private static TrackSample[] Linear(double east, double north, double heading, double speed, double duration = 10)
        {
            return new[] { Sample(0, east, north, heading, speed), Sample(duration, east + speed * Sin(heading) * duration, north + speed * Cos(heading) * duration, heading, speed) };
        }

        private static TrackSample Sample(double time, double east, double north, double cog, double speed, float? hdg = null, bool fromCog = false)
        {
            return new TrackSample(new SimTime(time), new GeoCoord(0, 0), new EnuPosition(east, north), new Double2(speed * Sin(cog), speed * Cos(cog)), (float)speed, (float)cog, hdg ?? (float)cog, 0, SampleProvenance.Presumed, TimeQuality.Estimated, fromCog);
        }

        private static EnvironmentState Environment(double time, float visibility)
        {
            return new EnvironmentState(new SimTime(time), "虚构环境", visibility, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
        }

        private static double Sin(double deg) { return Math.Sin(deg * Math.PI / 180); }
        private static double Cos(double deg) { return Math.Cos(deg * Math.PI / 180); }
    }
}

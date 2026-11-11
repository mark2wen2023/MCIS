using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Colreg;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Xunit;
using static Mcis.Acceptance.W1.Fx;

namespace Mcis.Acceptance.W1
{
    /// <summary>
    /// W1 复测（Gemini bot，2026-11-11）：覆盖架构师裁定 A1/A3/A4/A5/A6/A7 与 D03/D04/D05。
    /// 全部航迹为合成虚构数据（虚构甲船/虚构乙船）。预期值由夹具几何或独立相对运动公式给出，不取自被测代码。
    /// </summary>
    public sealed class RetestAcceptanceTests
    {
        private static Ship CrossTgt() => CollisionTarget(45, 2828.4, 400);
        private static readonly ColregThresholds Loose = new ColregThresholds(safePassingDcpaNm: 0.001, clearDistanceNm: 0.001);

        private static ColregAnalysisReport Req(TrackSample[] own, TrackSample[] tgt, ColregThresholds th = null,
            double? vis = 8, bool? inSight = true, bool narrow = false, IReadOnlyList<ColregInSightSample> sight = null,
            IReadOnlyList<EnuPosition> centerline = null, string caseId = "CASE-RT-001", IReadOnlyList<string> evidence = null)
        {
            var r = new ColregEngine().Analyze(new ColregAnalysisRequest(Own, Tgt, own, tgt, th, null, vis, inSight, narrow,
                null, sight, centerline, caseId, evidence));
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            return r.Value;
        }

        // ================= A1 局面锁定 =================

        /// <summary>A1 / R13(d)+R15：交叉中直航船乙在 R17(a)(ii) 阶段右转 60°，几何上本船渐落到其正横后，局面仍锁定为交叉、角色不变。</summary>
        [Fact]
        public void A1_CrossingDoesNotBecomeOvertaking_WhileRiskPersists()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(450), CrossTgt().Order(250, 330).Run(450));
            Assert.DoesNotContain(r.TimeBands, b => b.Situation == EncounterSituation.Overtaking);
            foreach (var b in r.TimeBands.Where(b => b.Situation != EncounterSituation.NoCollisionRisk))
            {
                Assert.Equal(EncounterSituation.Crossing, b.Situation);
                Assert.Equal(TrafficRole.GiveWay, b.OwnRole);
                Assert.Equal(TrafficRole.StandOn, b.TargetRole);
                Assert.Equal(Own, b.GiveWayVesselId);
                Assert.Equal(Tgt, b.StandOnVesselId);
            }
        }

        /// <summary>A1 / R15+R16：让路船甲右转 60°，危险持续期间角色不互换（原 D01 场景），乙不出现 R16 不满足。</summary>
        [Fact]
        public void A1_GiveWayTurn_RolesLockedUntilRiskEnds()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Order(250, 60).Run(450), CrossTgt().Run(450));
            foreach (var b in r.TimeBands.Where(b => b.Situation != EncounterSituation.NoCollisionRisk))
                Assert.True(b.Situation == EncounterSituation.Crossing && b.OwnRole == TrafficRole.GiveWay, Describe(r));
            Assert.DoesNotContain(Checks(r, ColregRuleId.R16, Tgt), c => c.Status == RuleCheckStatus.NotSatisfied);
        }

        /// <summary>A1：危险解除后再形成须重新判定（追越 → 无危险 → 新一次危险不得沿用追越）。</summary>
        [Fact]
        public void A1_RiskReformsAfterRelease_IsReclassified()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(900), new Ship(30, -1000, 0, 10).Order(500, 180).Run(900));
            int iNo = r.TimeBands.ToList().FindIndex(b => b.Situation == EncounterSituation.NoCollisionRisk);
            Assert.True(iNo > 0, Describe(r));
            var later = r.TimeBands.Skip(iNo + 1).FirstOrDefault(b => b.Situation != EncounterSituation.NoCollisionRisk);
            Assert.NotNull(later);
            Assert.NotEqual(EncounterSituation.Overtaking, later.Situation);
            Assert.NotEqual(r.TimeBands[0].BandId, later.BandId);
        }

        /// <summary>A1 例外 / R11+R19(a)：显式互见序列 155 s 由未互见变互见 → 在 155 s 精确开新带并按互见重判（对遇，R14）。</summary>
        [Fact]
        public void A1_NotInSightToInSight_OpensNewBandAtExactTime()
        {
            var sight = new[] { new ColregInSightSample(new SimTime(0), false), new ColregInSightSample(new SimTime(155), true) };
            var r = Req(new Ship(0, 0, 0, 5).Run(300), CollisionTarget(0, 4000, 400).Run(300), vis: 1.0, inSight: null, sight: sight);
            Assert.Equal(2, r.TimeBands.Count);
            Assert.Equal(EncounterSituation.RestrictedVisibility, r.TimeBands[0].Situation);
            Assert.False(r.TimeBands[0].InSight);
            Assert.Contains(ColregRuleId.R19, r.TimeBands[0].ApplicableRules);
            Assert.Equal(155, r.TimeBands[0].EndTime.Seconds, 9);
            Assert.Equal(155, r.TimeBands[1].StartTime.Seconds, 9);
            Assert.Equal(EncounterSituation.HeadOn, r.TimeBands[1].Situation);
            Assert.True(r.TimeBands[1].InSight);
            Assert.Contains(ColregRuleId.R14, r.TimeBands[1].ApplicableRules);
            Assert.DoesNotContain(ColregRuleId.R19, r.TimeBands[1].ApplicableRules);
        }

        /// <summary>D04：未给互见标志、能见度 1 nm，距离 ≤ 1 nm 时推导互见。独立计算：(4000−1852)/10 = 214.8 s，网格 10 s → 开带于 (214.8, 220]。</summary>
        [Fact]
        public void D04_DerivedInSight_DistanceWithinVisibility()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(300), CollisionTarget(0, 4000, 400).Run(300), vis: 1.0, inSight: null);
            Assert.Equal(EncounterSituation.RestrictedVisibility, r.TimeBands[0].Situation);
            var ho = r.TimeBands.Single(b => b.Situation == EncounterSituation.HeadOn);
            Assert.InRange(ho.StartTime.Seconds, 214.8, 220.0 + 1e-9);
            Assert.True(ho.InSight);
        }

        /// <summary>D03 / R11：能见度 1 nm 但显式互见 → 适用 R13–R17（对遇 R14），不适用 R19。</summary>
        [Fact]
        public void D03_ExplicitInSight_InRestrictedVisibility_UsesSectionII()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(100), CollisionTarget(0, 4000, 400).Run(100), vis: 1.0, inSight: true);
            Assert.Equal(EncounterSituation.HeadOn, r.TimeBands[0].Situation);
            Assert.DoesNotContain(ColregRuleId.R19, r.TimeBands[0].ApplicableRules);
        }

        // ================= A3 正船首/正船尾双视角 =================

        /// <summary>A3 / R15：他船在本船正船首（0°，本船视角无左右舷），他船看本船在其左舷 → 他船直航、本船让路；无矛盾不标存疑。</summary>
        [Fact]
        public void A3_TargetDeadAhead_UsesTargetView()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(200), new Ship(0, 2000, 270, 5).Run(200));
            var b = r.TimeBands[0];
            Assert.Equal(EncounterSituation.Crossing, b.Situation);
            Assert.Equal(TrafficRole.GiveWay, b.OwnRole);
            Assert.Equal(TrafficRole.StandOn, b.TargetRole);
            Assert.False(b.Doubt);
            Assert.Contains("轴线", b.Basis);
        }

        /// <summary>A3 / R15 镜像：本船在他船正船首，本船看他船在右舷 → 本船让路。</summary>
        [Fact]
        public void A3_OwnDeadAheadOfTarget_UsesOwnView()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(200), new Ship(2000, 0, 270, 5).Run(200));
            var b = r.TimeBands[0];
            Assert.Equal(EncounterSituation.Crossing, b.Situation);
            Assert.Equal(TrafficRole.GiveWay, b.OwnRole);
            Assert.Equal(TrafficRole.StandOn, b.TargetRole);
        }

        /// <summary>A3 / D11：两船互见对方均在右舷（航向差 160°，非对遇）→ 视角矛盾，标 Doubt，让路/直航为空；R15–R17 一律 NeedsReview（W1.1 裁定补充①，原断言期望 R15 Partial）。</summary>
        [Fact]
        public void A3_ContradictoryViews_FlaggedDoubt()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(200), new Ship(1000, 1732.05, 200, 5).Run(200));
            var b = r.TimeBands[0];
            Assert.Equal(EncounterSituation.Crossing, b.Situation);
            Assert.True(b.Doubt);
            Assert.Contains("存疑", b.Basis);
            Assert.Null(b.GiveWayVesselId);
            Assert.Null(b.StandOnVesselId);
            Assert.Equal(TrafficRole.Undetermined, b.OwnRole);
            Assert.Equal(TrafficRole.Undetermined, b.TargetRole);
            foreach (var id in new[] { ColregRuleId.R15, ColregRuleId.R16, ColregRuleId.R17 })
                Assert.All(Checks(r, id, Own).Concat(Checks(r, id, Tgt)).Where(c => c.Status != RuleCheckStatus.NotApplicable),
                    c => Assert.Equal(RuleCheckStatus.NeedsReview, c.Status));
        }

        // ================= A4 对遇存疑 R14(c) =================

        /// <summary>A4 / R14(a)(c)：反向航行，他船相对方位 15°/20°/22.5°/25°。15° 在前方扇区→对遇不存疑；20°/22.5° → 对遇+Doubt；25° → 非对遇。</summary>
        [Theory]
        [InlineData(15.0, EncounterSituation.HeadOn, false)]
        [InlineData(20.0, EncounterSituation.HeadOn, true)]
        [InlineData(22.5, EncounterSituation.HeadOn, true)]
        [InlineData(25.0, EncounterSituation.Crossing, true)]
        public void A4_HeadOnDoubtSector(double bearing, EncounterSituation expected, bool doubt)
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(150), new Ship(2000 * Sin(bearing), 2000 * Cos(bearing), 180, 5).Run(150));
            Assert.Equal(expected, r.TimeBands[0].Situation);
            Assert.Equal(doubt, r.TimeBands[0].Doubt);
        }

        /// <summary>A4 可配：HeadOnDoubtBearingDeg=30 时 25° 也按对遇存疑。</summary>
        [Fact]
        public void A4_DoubtSector_Configurable()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(150), new Ship(2000 * Sin(25), 2000 * Cos(25), 180, 5).Run(150),
                new ColregThresholds(headOnDoubtBearingDeg: 30));
            Assert.Equal(EncounterSituation.HeadOn, r.TimeBands[0].Situation);
            Assert.True(r.TimeBands[0].Doubt);
        }

        /// <summary>A4 前提：航向差须 ≤6°。他船方位 10° 但航向差 8°（他船航向 188°）→ 不按对遇。</summary>
        [Fact]
        public void A4_HeadingDifferenceAbove6_NotHeadOn()
        {
            double b = 10, h = 188;
            var tgt = new Ship(2000 * Sin(b), 2000 * Cos(b), h, 5);
            var r = Ok(new Ship(0, 0, 0, 5).Run(150), tgt.Run(150));
            Assert.NotEqual(EncounterSituation.HeadOn, r.TimeBands[0].Situation);
        }

        // ================= A5 阈值 =================

        /// <summary>A5 碰撞危险 0&lt;TCPA≤720 s：反向横距 0.25 nm、相对 10 m/s、初距 9000 m → TCPA=900−t；t&lt;180 无危险，180 s 起危险（含边界）。</summary>
        [Fact]
        public void A5_CollisionRisk_TcpaUpperBound720()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(400), new Ship(463, 9000, 180, 5).Run(400));
            Assert.Equal(EncounterSituation.NoCollisionRisk, r.TimeBands[0].Situation);
            Assert.Equal(180, r.TimeBands[0].EndTime.Seconds, 6);
            Assert.Equal(EncounterSituation.HeadOn, r.TimeBands[1].Situation);
        }

        /// <summary>A5 碰撞危险 DCPA&lt;1 nm：横距 1.05 nm 的反向会遇无危险；0.95 nm 有危险。</summary>
        [Theory]
        [InlineData(0.95, false)]
        [InlineData(1.05, true)]
        public void A5_CollisionRisk_Dcpa1nm(double offsetNm, bool noRisk)
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(100), new Ship(offsetNm * 1852, 5000, 180, 5).Run(100));
            Assert.Equal(noRisk, r.TimeBands[0].Situation == EncounterSituation.NoCollisionRisk);
        }

        /// <summary>
        /// A5 紧迫局面 DCPA&lt;0.3 nm 且 TCPA≤360 s：横距 0.25 nm、初距 5000 m → TCPA=500−t。
        /// 独立预期：CollisionRisk [0,140)，CloseQuarters [140,440)，ImmediateDanger（TCPA≤60 s 代理）[440,500)。横距 0.35 nm 不出现紧迫。
        /// </summary>
        [Fact]
        public void A5_CloseQuarters_StagesAndBoundaries()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(600), new Ship(463, 5000, 180, 5).Run(600));
            var cq = r.DangerStages.Single(s => s.Stage == ColregDangerStage.CloseQuarters);
            Assert.Equal(140, cq.StartTime.Seconds, 6);
            Assert.Equal(440, cq.EndTime.Seconds, 6);
            var id = r.DangerStages.Single(s => s.Stage == ColregDangerStage.ImmediateDanger);
            Assert.Equal(440, id.StartTime.Seconds, 6);
            Assert.False(string.IsNullOrEmpty(id.StageId));
            Assert.Equal(ColregDangerStage.ImmediateDanger, r.TimeBands[0].DangerStage);
            Assert.Equal(EncounterSituation.HeadOn, r.TimeBands[0].Situation); // 紧迫不拆会遇类型（设计说明）

            var wide = Ok(new Ship(0, 0, 0, 5).Run(600), new Ship(648, 5000, 180, 5).Run(600));
            Assert.DoesNotContain(wide.DangerStages, s => s.Stage == ColregDangerStage.CloseQuarters || s.Stage == ColregDangerStage.ImmediateDanger);
        }

        /// <summary>A5 / R8(b) 60 s 滑窗：一次连续右转 40°，转向率 0.4°/s 时任一 60 s 窗内仅 24° → 非明显；转向率 1°/s → 明显。</summary>
        [Theory]
        [InlineData(0.4, false)]
        [InlineData(1.0, true)]
        public void A5_TurnWindow60s(double rate, bool substantial)
        {
            var own = new Ship(0, 0, 0, 5) { TurnRate = rate }.Order(40, 40);
            var r = Ok(own.Run(450), CrossTgt().Run(450), Loose);
            Assert.Contains("明显行动=" + substantial, Checks(r, ColregRuleId.R8, Own).First().Explanation);
        }

        /// <summary>A5 / R8(b)"避免一连串的小幅度转向"：三次 15° 右转相隔 90 s，累计 45° 但不累计为明显行动。</summary>
        [Fact]
        public void A5_SeriesOfSmallTurns_NotCumulated()
        {
            var own = new Ship(0, 0, 0, 5).Order(20, 15).Order(110, 30).Order(200, 45);
            var r = Ok(own.Run(450), CrossTgt().Run(450), Loose);
            var r8 = Checks(r, ColregRuleId.R8, Own).First();
            Assert.True(r8.ActualAction.HeadingChangeDeg > 40, Describe(r));
            Assert.Contains("明显行动=False", r8.Explanation);
        }

        /// <summary>A5 / R8(b) 变速 30% 初速：5 m/s 降至 3.6（28%）非明显；降至 3.4（32%）明显。</summary>
        [Theory]
        [InlineData(3.6, false)]
        [InlineData(3.4, true)]
        public void A5_SpeedChange30Percent(double newSpeed, bool substantial)
        {
            var own = new Ship(0, 0, 0, 5) { Accel = 5 }.Order(60, 0, newSpeed);
            var r = Ok(own.Run(450), CrossTgt().Run(450), Loose);
            Assert.Contains("明显行动=" + substantial, Checks(r, ColregRuleId.R8, Own).First().Explanation);
        }

        /// <summary>A5 默认阈值回显：1 nm/720 s、0.3 nm/360 s、30°、30%、60 s。</summary>
        [Fact]
        public void A5_DefaultThresholds()
        {
            var t = ColregThresholds.Default;
            Assert.Equal(1.0, t.CollisionRiskDcpaNm);
            Assert.Equal(720, t.CollisionRiskTcpaSeconds);
            Assert.Equal(0.3, t.CloseQuartersDcpaNm);
            Assert.Equal(360, t.CloseQuartersTcpaSeconds);
            Assert.Equal(30, t.SubstantialTurnDeg);
            Assert.Equal(0.3, t.SubstantialSpeedChangeFraction);
            Assert.Equal(60, t.SubstantialTurnWindowSeconds);
        }

        // ================= A6 规则目录 =================

        /// <summary>A6：目录须含 R5、R6、R7、R8、R9、R13–R19、R34/35（裁定原文"R13–R19"含 R18）。</summary>
        [Theory]
        [InlineData("R5")]
        [InlineData("R6")]
        [InlineData("R7")]
        [InlineData("R8")]
        [InlineData("R9")]
        [InlineData("R13")]
        [InlineData("R14")]
        [InlineData("R15")]
        [InlineData("R16")]
        [InlineData("R17")]
        [InlineData("R19")]
        [InlineData("R34_35")]
        public void A6_CatalogContainsRule(string rule)
        {
            Assert.Contains(ColregRules.Catalog, d => d.Id.ToString() == rule);
        }

        /// <summary>W1-D09 / A6：裁定范围"R13–R19"含 R18（船舶之间的责任），目录与 ColregRuleId 均缺；失控/操限船无法表达（海力5 真实案例即失控船）。</summary>
        [Fact]
        [Trait("Category", "KnownDefect")]
        public void W1_D09_CatalogContainsR18()
        {
            Assert.Contains(ColregRules.Catalog, d => d.Id.ToString() == "R18");
        }

        /// <summary>A6 / R5、R34–35：无瞭望/声号资料时 NotAssessable 并列出所需证据；R6 只出需研判并列出所需资料。</summary>
        [Fact]
        public void A6_NoData_NotAssessableWithRequiredEvidence()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(200), CrossTgt().Run(200));
            foreach (var v in new[] { Own, Tgt })
            {
                var r5 = Checks(r, ColregRuleId.R5, v).Where(c => c.Status != RuleCheckStatus.NotApplicable).ToList();
                Assert.NotEmpty(r5);
                Assert.All(r5, c => { Assert.Equal(RuleCheckStatus.NotAssessable, c.Status); Assert.Contains("VDR", c.Explanation); });
                var s = Checks(r, ColregRuleId.R34_35, v).Where(c => c.Status != RuleCheckStatus.NotApplicable).ToList();
                Assert.NotEmpty(s);
                Assert.All(s, c => { Assert.Equal(RuleCheckStatus.NotAssessable, c.Status); Assert.Contains("声号", c.Explanation); });
                var r6 = Checks(r, ColregRuleId.R6, v).Where(c => c.Status != RuleCheckStatus.NotApplicable).ToList();
                Assert.NotEmpty(r6);
                Assert.All(r6, c => { Assert.True(c.Status == RuleCheckStatus.NeedsReview || c.Status == RuleCheckStatus.NotAssessable); Assert.Contains("操纵性能", c.Explanation); });
                var r7 = Checks(r, ColregRuleId.R7, v).Where(c => c.Status != RuleCheckStatus.NotApplicable).ToList();
                Assert.NotEmpty(r7);
                Assert.All(r7, c => Assert.Contains("DCPA", c.Explanation));
            }
        }

        /// <summary>A6 / R9(a)：狭水道且给航道中心线（南北向，E=0）→ 本船北行在中线以东（右侧）满足、以西不满足；未给中心线 NotAssessable；未标狭水道 NotApplicable。</summary>
        [Fact]
        public void A6_R9_CenterlineKeepRight()
        {
            var line = new[] { new EnuPosition(0, -5000), new EnuPosition(0, 5000) };
            var tgtShip = new Ship(-300, 3000, 180, 5);
            var right = Req(new Ship(100, 0, 0, 5).Run(200), tgtShip.Run(200), narrow: true, centerline: line);
            Assert.All(Checks(right, ColregRuleId.R9, Own), c => Assert.Equal(RuleCheckStatus.Satisfied, c.Status));
            Assert.All(Checks(right, ColregRuleId.R9, Tgt), c => Assert.Equal(RuleCheckStatus.Satisfied, c.Status)); // 南行在 E<0 为其右侧
            var left = Req(new Ship(-100, 0, 0, 5).Run(200), tgtShip.Run(200), narrow: true, centerline: line);
            Assert.Contains(Checks(left, ColregRuleId.R9, Own), c => c.Status == RuleCheckStatus.NotSatisfied);
            var noLine = Req(new Ship(100, 0, 0, 5).Run(200), tgtShip.Run(200), narrow: true);
            Assert.All(Checks(noLine, ColregRuleId.R9, Own), c => Assert.Equal(RuleCheckStatus.NotAssessable, c.Status));
            var notNarrow = Req(new Ship(100, 0, 0, 5).Run(200), tgtShip.Run(200), centerline: line);
            Assert.All(Checks(notNarrow, ColregRuleId.R9, Own), c => Assert.Equal(RuleCheckStatus.NotApplicable, c.Status));
        }

        // ================= A7 确定性 ID / Draft =================

        /// <summary>A7：同输入两次分析 ID 全同；不同 caseId 时 band/check/stage ID 全不同；报告内 ID 唯一；确认状态恒为 Draft；证据 ID 原样（含顺序与重复）。</summary>
        [Fact]
        public void A7_DeterministicIds_DraftStatus_EvidencePassThrough()
        {
            var ev = new[] { "EV-002", "EV-001", "EV-002" };
            Func<string, ColregAnalysisReport> run = cid => Req(new Ship(0, 0, 0, 5).Order(60, 60).Run(450), CrossTgt().Run(450), caseId: cid, evidence: ev);
            var a = run("CASE-RT-001"); var b = run("CASE-RT-001"); var c = run("CASE-RT-002");
            Func<ColregAnalysisReport, string[]> ids = r => r.TimeBands.Select(x => x.BandId)
                .Concat(r.RuleChecks.Select(x => x.CheckId)).Concat(r.DangerStages.Select(x => x.StageId)).ToArray();
            Assert.Equal(ids(a), ids(b));
            Assert.All(ids(a), x => Assert.False(string.IsNullOrEmpty(x)));
            Assert.Empty(ids(a).Intersect(ids(c)));
            Assert.All(a.RuleChecks, x => Assert.Equal(ColregReviewStatus.Draft, x.ReviewStatus));
            Assert.All(a.RuleChecks, x => Assert.Equal(ev, x.EvidenceIds.ToArray()));
            Assert.All(a.RuleChecks, x => Assert.Equal(x.StartTime.Seconds, x.AtTimeSec));
            var dup = a.RuleChecks.GroupBy(x => x.CheckId).Where(g => g.Count() > 1).Select(g => g.Key).ToList();
            Assert.True(dup.Count == 0, "重复 checkId：" + string.Join(" ; ", dup));
            Assert.Equal(a.TimeBands.Count, a.TimeBands.Select(x => x.BandId).Distinct().Count());
        }

        /// <summary>A7：未互见带也有确定性 ID 与 Draft；不同船号顺序产生不同 ID（不以船名归一化）。</summary>
        [Fact]
        public void A7_IdsDependOnVesselOrder()
        {
            var o = new Ship(0, 0, 0, 5).Run(100); var t = CollisionTarget(0, 4000, 400).Run(100);
            var ab = new ColregEngine().Analyze(new ColregAnalysisRequest("A", "B", o, t, vesselsInSight: false, visibilityNm: 0.5, caseId: "CASE-RT-003")).Value;
            var ba = new ColregEngine().Analyze(new ColregAnalysisRequest("B", "A", o, t, vesselsInSight: false, visibilityNm: 0.5, caseId: "CASE-RT-003")).Value;
            Assert.NotEqual(ab.TimeBands[0].BandId, ba.TimeBands[0].BandId);
            Assert.All(ab.RuleChecks, x => Assert.Equal(ColregReviewStatus.Draft, x.ReviewStatus));
        }

        // ================= D05 R19(d) 前提 =================

        /// <summary>D05 / R19(d)：无碰撞危险且无紧迫局面时，R19(d)(i)(ii) 均为 NotApplicable（本船左转亦然）。</summary>
        [Fact]
        public void D05_R19d_NotApplicableWithoutRisk()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Order(30, 340).Run(200), new Ship(4000, 4000, 180, 5).Run(200), vis: 0.5, inSight: false);
            Assert.All(Checks(r, ColregRuleId.R19, Own).Where(c => c.Clause.StartsWith("R19(d)")),
                c => Assert.Equal(RuleCheckStatus.NotApplicable, c.Status));
        }

        /// <summary>D05 对照 / R19(d)(i)：有碰撞危险时，对正横前他船左转 → 不满足（前提成立时仍判定）。</summary>
        [Fact]
        public void D05_R19d_AppliesWithRisk()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Order(60, 330).Run(300), CollisionTarget(10, 4000, 400).Run(300), vis: 0.5, inSight: false);
            Assert.Contains(Checks(r, ColregRuleId.R19, Own), c => c.Clause == "R19(d)(i)" && c.Status == RuleCheckStatus.NotSatisfied);
        }
        // ================= 复测新缺陷（KnownDefect，保留失败） =================

        private static (ColregAnalysisReport ab, ColregAnalysisReport ba) Swapped(TrackSample[] a, TrackSample[] b)
        {
            var e = new ColregEngine();
            return (e.Analyze(new ColregAnalysisRequest("A", "B", a, b, vesselsInSight: true, visibilityNm: 8)).Value,
                    e.Analyze(new ColregAnalysisRequest("B", "A", b, a, vesselsInSight: true, visibilityNm: 8)).Value);
        }

        /// <summary>
        /// W1-D10 / R14(c)：对遇存疑扇区只检查"本船"视角。本船看他船 20°、他船看本船 26°（航向差 6°）→ AB 判对遇，
        /// 交换本船/他船后判交叉。局面不应随输入顺序改变。
        /// </summary>
        [Fact]
        [Trait("Category", "KnownDefect")]
        public void W1_D10_HeadOnDoubt_SymmetricUnderSwap()
        {
            var (ab, ba) = Swapped(new Ship(0, 0, 0, 5).Run(150), new Ship(2000 * Sin(20), 2000 * Cos(20), 174, 5).Run(150));
            Assert.Equal(ab.TimeBands[0].Situation, ba.TimeBands[0].Situation);
        }

        /// <summary>
        /// W1-D11 / R15、A3：两船视角矛盾（互见对方均在右舷）时，让路角色总落在请求里的"本船"上，交换顺序后让路船随之改变，
        /// 并据此给该船出 R16 NotSatisfied。存疑时角色不应由输入顺序决定。
        /// </summary>
        [Fact]
        [Trait("Category", "KnownDefect")]
        public void W1_D11_ContradictoryViews_RolesIndependentOfOrder()
        {
            var (ab, ba) = Swapped(new Ship(0, 0, 0, 5).Run(200), new Ship(1000, 1732.05, 200, 5).Run(200));
            Assert.Equal(ab.TimeBands[0].GiveWayVesselId, ba.TimeBands[0].GiveWayVesselId);
            Assert.Equal(ab.TimeBands[0].StandOnVesselId, ba.TimeBands[0].StandOnVesselId);
        }
    }
}

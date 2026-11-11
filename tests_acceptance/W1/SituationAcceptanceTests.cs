using System.Linq;
using Mcis.Domain.Colreg;
using Xunit;
using static Mcis.Acceptance.W1.Fx;

namespace Mcis.Acceptance.W1
{
    /// <summary>会遇局面判定（R13/R14/R15/R19）验收。示例数据·虚构。</summary>
    public sealed class SituationAcceptanceTests
    {
        // ---------- R14 对遇 ----------

        /// <summary>R14(a)(b)：反向或接近反向航向、他船在正前方 → 对遇，双方均须向右转向；无直航船。</summary>
        [Fact]
        public void R14_ExactReciprocal_IsHeadOn_BothMustAlterToStarboard()
        {
            var tgt = CollisionTarget(0, 4000, 400);
            var r = Ok(new Ship(0, 0, 0, 5).Run(300), tgt.Run(300));
            var b = r.TimeBands.First();
            Assert.Equal(EncounterSituation.HeadOn, b.Situation);
            Assert.Equal(TrafficRole.BothActionRequired, b.OwnRole);
            Assert.Equal(TrafficRole.BothActionRequired, b.TargetRole);
            Assert.Contains(ColregRuleId.R14, b.ApplicableRules);
            Assert.DoesNotContain(ColregRuleId.R17, b.ApplicableRules);
            foreach (var v in new[] { Own, Tgt })
                Assert.Contains("右", Checks(r, ColregRuleId.R14, v).First().ExpectedAction);
        }

        /// <summary>R14(b) 夜间"桅灯成一直线或接近一直线"以船首向差 ≤6° 近似：边界内侧（含 6.0°）为对遇，外侧 6.1° 为交叉。</summary>
        [Theory]
        [InlineData(0.0, true)]
        [InlineData(5.9, true)]
        [InlineData(6.0, true)]
        [InlineData(-6.0, true)]
        [InlineData(6.1, false)]
        [InlineData(-6.1, false)]
        [InlineData(10.0, false)]
        public void R14_HeadingDifferenceBoundary_SixDegrees(double offset, bool headOn)
        {
            // 他船以 180+offset 航向驶向碰撞点(0,2000)，T=400 s；方位始终在船首 ±15° 内。
            double h = 180 + offset;
            var tgt = new Ship(-5 * Sin(h) * 400, 2000 - 5 * Cos(h) * 400, h, 5);
            var r = Ok(new Ship(0, 0, 0, 5).Run(300), tgt.Run(300));
            var s = r.TimeBands.First().Situation;
            if (headOn) Assert.Equal(EncounterSituation.HeadOn, s);
            else Assert.Equal(EncounterSituation.Crossing, s);
        }

        /// <summary>R14(b)：船首向反向但他船明显偏在船首一侧（桅灯不可能成一直线，方位 30°）→ 不按对遇。</summary>
        [Fact]
        public void R14_ReciprocalButWellOffBow_IsNotHeadOn()
        {
            // 他船位于方位 30°、距 1400 m，航向 180 → 横距 700 m=0.38 nm (<0.5 有碰撞危险)
            var tgt = new Ship(1400 * Sin(30), 1400 * Cos(30), 180, 5);
            var r = Ok(new Ship(0, 0, 0, 5).Run(60), tgt.Run(60));
            Assert.NotEqual(EncounterSituation.HeadOn, r.TimeBands.First().Situation);
        }

        /// <summary>航向 359°→1° 跨零：本船 359°、他船 179°（反向，差 180°）应判对遇，船首向差证据为 180。</summary>
        [Fact]
        public void R14_HeadingWrapAroundZero_359vs179_IsHeadOn()
        {
            var own = new Ship(0, 0, 359, 5);
            // 碰撞点：本船 400 s 后位置
            double pe = 5 * Sin(359) * 400, pn = 5 * Cos(359) * 400;
            var tgt = new Ship(pe - 5 * Sin(179) * 400, pn - 5 * Cos(179) * 400, 179, 5);
            var r = Ok(own.Run(300), tgt.Run(300));
            Assert.Equal(EncounterSituation.HeadOn, r.TimeBands.First().Situation);
            Assert.Equal(180.0, Checks(r, ColregRuleId.R14, Own).First().Evidence.HeadingDifferenceDeg, 3);
        }

        // ---------- R15 交叉 ----------

        /// <summary>R15：他船在本船右舷（方位 45°）→ 本船让路、他船直航。</summary>
        [Fact]
        public void R15_TargetOnStarboard_OwnGivesWay()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(300), CollisionTarget(45, 2828.4, 400).Run(300));
            var b = r.TimeBands.First();
            Assert.Equal(EncounterSituation.Crossing, b.Situation);
            Assert.Equal(TrafficRole.GiveWay, b.OwnRole);
            Assert.Equal(TrafficRole.StandOn, b.TargetRole);
            Assert.Contains(ColregRuleId.R15, b.ApplicableRules);
            Assert.Contains(ColregRuleId.R16, b.ApplicableRules);
            Assert.Contains(ColregRuleId.R17, b.ApplicableRules);
        }

        /// <summary>R15/R17：他船在本船左舷（方位 315°）→ 本船直航、他船让路。</summary>
        [Fact]
        public void R15_TargetOnPort_OwnStandsOn()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(300), CollisionTarget(315, 2828.4, 400).Run(300));
            var b = r.TimeBands.First();
            Assert.Equal(EncounterSituation.Crossing, b.Situation);
            Assert.Equal(TrafficRole.StandOn, b.OwnRole);
            Assert.Equal(TrafficRole.GiveWay, b.TargetRole);
            Assert.Equal(RuleCheckStatus.NotApplicable, Checks(r, ColregRuleId.R15, Own).First().Status);
        }

        /// <summary>
        /// R15 + R8(d)/R16"直至最后驶过让清"：交叉局面的让路/直航义务确定后，不应因让路船自己的（迟到但大幅的）右转使相对方位落到左舷而互换角色。
        /// </summary>
        [Fact]
        [Trait("Category", "KnownDefect")]
        public void W1_D01_Crossing_RolesMustNotFlipAfterGiveWayStarboardTurn()
        {
            var tgt = CollisionTarget(45, 2828.4, 400);
            var r = Ok(new Ship(0, 0, 0, 5).Order(250, 60).Run(450), tgt.Run(450));
            Assert.DoesNotContain(r.TimeBands, b => b.Situation == EncounterSituation.Crossing && b.OwnRole == TrafficRole.StandOn);
            // 原直航船（乙）不应被判 R16 让路义务不满足
            Assert.DoesNotContain(Checks(r, ColregRuleId.R16, Tgt), c => c.Status == RuleCheckStatus.NotSatisfied);
        }

        /// <summary>
        /// R14(a)：对遇中一船按规定右转后，局面不应改判为"交叉"并把正确右转的船定为直航船、保向的他船定为让路船。
        /// </summary>
        [Fact]
        [Trait("Category", "KnownDefect")]
        public void W1_D02_HeadOn_ProperStarboardTurnMustNotReclassifyToCrossingWithSwappedRoles()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Order(100, 30).Run(450), CollisionTarget(0, 4000, 400).Run(450));
            Assert.DoesNotContain(r.TimeBands, b => b.Situation == EncounterSituation.Crossing);
            Assert.DoesNotContain(Checks(r, ColregRuleId.R16, Tgt), c => c.Status == RuleCheckStatus.NotSatisfied);
        }

        // ---------- R13 追越 ----------

        /// <summary>R13(b)(c)：来自正横后大于 22.5°（相对方位 112.5°–247.5°）为追越；存疑按追越 → 边界闭区间。边界外侧为交叉。</summary>
        [Theory]
        [InlineData(112.49, EncounterSituation.Crossing)]
        [InlineData(112.51, EncounterSituation.Overtaking)]
        [InlineData(150.0, EncounterSituation.Overtaking)]
        [InlineData(180.0, EncounterSituation.Overtaking)]
        [InlineData(247.49, EncounterSituation.Overtaking)]
        [InlineData(247.51, EncounterSituation.Crossing)]
        public void R13_OvertakingSectorBoundaries(double bearing, EncounterSituation expected)
        {
            var tgt = CollisionTarget(bearing, 1000, 300);
            var r = Ok(new Ship(0, 0, 0, 5).Run(200), tgt.Run(200));
            var b = r.TimeBands.First();
            Assert.Equal(expected, b.Situation);
            if (expected == EncounterSituation.Overtaking)
            {
                Assert.Equal(TrafficRole.StandOn, b.OwnRole);   // 被追越
                Assert.Equal(TrafficRole.GiveWay, b.TargetRole); // 追越船
                Assert.Contains(ColregRuleId.R13, b.ApplicableRules);
            }
        }

        /// <summary>R13(a)：追越条款优先于交叉 —— 追越船即使位于被追越船右舷后方，也不得按 R15 让被追越船让路。</summary>
        [Fact]
        public void R13_OvertakingFromStarboardQuarter_OverridesCrossing()
        {
            var tgt = CollisionTarget(135, 1000, 300);
            var r = Ok(new Ship(0, 0, 0, 5).Run(200), tgt.Run(200));
            Assert.Equal(EncounterSituation.Overtaking, r.TimeBands.First().Situation);
            Assert.DoesNotContain(ColregRuleId.R15, r.TimeBands.First().ApplicableRules);
        }

        /// <summary>R13(d)：追越局面一旦确定，此后方位变化（追越船到正横、再横越前方）不使其成为交叉船，直至驶过让清。</summary>
        [Fact]
        public void R13_OvertakingPersistsUntilPastAndClear()
        {
            // 他船在本船右后方 100 m 横距、1000 m 后，航速 10 → 200 s 时到正横，随后左转 300° 横越本船船首
            var own = new Ship(0, 0, 0, 5);
            var tgt = new Ship(100, -1000, 0, 10).Order(200, 300);
            var r = Ok(own.Run(600), tgt.Run(600));
            var first = r.TimeBands.First();
            Assert.Equal(EncounterSituation.Overtaking, first.Situation);
            Assert.DoesNotContain(r.TimeBands, b => b.Situation == EncounterSituation.Crossing || b.Situation == EncounterSituation.HeadOn);
            // 追越船角色始终是让路船
            Assert.All(r.TimeBands.Where(b => b.Situation == EncounterSituation.Overtaking), b => Assert.Equal(TrafficRole.GiveWay, b.TargetRole));
        }

        /// <summary>R13(d)：驶过让清后追越身份解除 → 最后一段为无碰撞危险。</summary>
        [Fact]
        public void R13_OvertakingReleasedAfterClear()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(600), new Ship(100, -1000, 0, 10).Run(600));
            Assert.Equal(EncounterSituation.Overtaking, r.TimeBands.First().Situation);
            Assert.Equal(EncounterSituation.NoCollisionRisk, r.TimeBands.Last().Situation);
        }

        // ---------- R19 能见度不良 ----------

        /// <summary>R19(a)/R11：未互见（显式 false）时适用 R19，优先于 R13–R15（对遇几何）。</summary>
        [Fact]
        public void R19_NotInSight_OverridesHeadOn()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(300), CollisionTarget(0, 4000, 400).Run(300), vis: 1.0, inSight: false);
            var b = r.TimeBands.First();
            Assert.Equal(EncounterSituation.RestrictedVisibility, b.Situation);
            Assert.Contains(ColregRuleId.R19, b.ApplicableRules);
            Assert.DoesNotContain(ColregRuleId.R14, b.ApplicableRules);
            Assert.All(r.RuleChecks.Where(c => c.RuleId == ColregRuleId.R13 || c.RuleId == ColregRuleId.R14 || c.RuleId == ColregRuleId.R15),
                c => Assert.Equal(RuleCheckStatus.NotApplicable, c.Status));
        }

        /// <summary>R19(a)：未互见时追越几何也不按 R13 分让路/直航（双方均有 R19 行动义务）。</summary>
        [Fact]
        public void R19_NotInSight_OverridesOvertaking()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(200), CollisionTarget(180, 1000, 300).Run(200), vis: 0.5, inSight: false);
            var b = r.TimeBands.First();
            Assert.Equal(EncounterSituation.RestrictedVisibility, b.Situation);
            Assert.Equal(TrafficRole.BothActionRequired, b.OwnRole);
            Assert.DoesNotContain(ColregRuleId.R13, b.ApplicableRules);
        }

        /// <summary>
        /// R11 + R19(a)：第二节（R11–R18）适用于"互见中的船舶"，R19 仅适用于"不在互见中"的船舶。能见度 1 nm 但已显式互见 → 应按 R14 对遇，而非 R19。
        /// （原型 11 也明确区分"能见度不良·未互见 R19"与"互见·对遇 R14"。）
        /// </summary>
        [Fact]
        [Trait("Category", "KnownDefect")]
        public void W1_D03_RestrictedVisibilityButExplicitlyInSight_AppliesSectionII()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(300), CollisionTarget(0, 1500, 150).Run(140), vis: 1.0, inSight: true);
            Assert.Equal(EncounterSituation.HeadOn, r.TimeBands.First().Situation);
        }

        /// <summary>
        /// 原型 11 时间带"能见度不良·未互见 R19 → 互见·对遇 R14"：互见状态须能随时间变化（如环境序列或距离≤能见度时转为互见）。
        /// 能见度 1 nm 恒定、两船对驶从 2.2 nm 接近 → 距离进入 1 nm 后应出现互见的对遇时间带。
        /// </summary>
        [Fact]
        [Trait("Category", "KnownDefect")]
        public void W1_D04_InSightMustBeAbleToChangeOverTime_PrototypeBandSequence()
        {
            var env = new[] { Env(0, 1.0f) };
            var r = Ok(new Ship(0, 0, 0, 5).Run(380), CollisionTarget(0, 4000, 400).Run(380), vis: null, inSight: null, env: env);
            Assert.Equal(EncounterSituation.RestrictedVisibility, r.TimeBands.First().Situation);
            Assert.Contains(r.TimeBands, b => b.Situation == EncounterSituation.HeadOn);
        }

        /// <summary>能见度阈值：低于 2.0 nm（默认）且未给互见标志 → R19；等于 2.0 nm 不按能见度不良（阈值为严格小于，已在假设中说明）。</summary>
        [Theory]
        [InlineData(1.99, EncounterSituation.RestrictedVisibility)]
        [InlineData(2.0, EncounterSituation.HeadOn)]
        public void R19_VisibilityThreshold(double vis, EncounterSituation expected)
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(300), CollisionTarget(0, 4000, 400).Run(300), vis: vis, inSight: null);
            Assert.Equal(expected, r.TimeBands.First().Situation);
        }

        /// <summary>无碰撞危险（平行远离/横距 2 nm）→ 不分让路直航，R13–R17 全部不适用。R7 前提。</summary>
        [Fact]
        public void NoRisk_NoRolesAssigned()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(200), new Ship(3704, 1000, 180, 5).Run(200));
            Assert.All(r.TimeBands, b => Assert.Equal(EncounterSituation.NoCollisionRisk, b.Situation));
            Assert.All(r.RuleChecks.Where(c => c.RuleId != ColregRuleId.R9), c => Assert.Equal(RuleCheckStatus.NotApplicable, c.Status));
        }
    }
}

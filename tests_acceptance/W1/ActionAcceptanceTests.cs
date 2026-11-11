using System.Linq;
using Mcis.Domain.Colreg;
using Xunit;
using static Mcis.Acceptance.W1.Fx;

namespace Mcis.Acceptance.W1
{
    /// <summary>应采取行动 vs 实际操纵（R8/R16/R17/R19(d)/R13 被追越船）验收。示例数据·虚构。</summary>
    public sealed class ActionAcceptanceTests
    {
        private static Ship CrossTgt() => CollisionTarget(45, 2828.4, 400); // 右舷来船，T=400 s 相撞

        // ---------- R16 ----------

        /// <summary>R16/R8(a)(b)(d)：让路船在 TCPA≈340 s 时右转 60°（及早、大幅、驶过距离 ≥0.5 nm、从直航船船尾驶过）→ R16、R15、R8 满足。</summary>
        [Fact]
        public void R16_EarlySubstantialStarboardTurn_Satisfied()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Order(60, 60).Run(450), CrossTgt().Run(450));
            var r16 = Checks(r, ColregRuleId.R16, Own).Where(c => c.Status != RuleCheckStatus.NotApplicable).ToList();
            Assert.NotEmpty(r16);
            Assert.All(r16, c => Assert.Equal(RuleCheckStatus.Satisfied, c.Status));
            Assert.Contains(Checks(r, ColregRuleId.R15, Own), c => c.Status == RuleCheckStatus.Satisfied);
            Assert.Contains(Checks(r, ColregRuleId.R8, Own), c => c.Status == RuleCheckStatus.Satisfied);
            Assert.Equal(TurnDirection.Starboard, r16[0].ActualAction.Turn);
            Assert.True(r16[0].Evidence.EarlyActionRemainingTcpaSeconds > 300, Describe(r));
        }

        /// <summary>R16"及早"：同样 60° 右转但在 TCPA≈70 s、距离 0.27 nm 时才采取 → R16 不满足（不得被判满足）。</summary>
        [Fact]
        public void R16_LateAction_NotSatisfied()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Order(330, 60).Run(450), CrossTgt().Run(450));
            var own = Checks(r, ColregRuleId.R16, Own).Where(c => c.Status != RuleCheckStatus.NotApplicable).ToList();
            Assert.Contains(own, c => c.Status == RuleCheckStatus.NotSatisfied);
            Assert.DoesNotContain(own, c => c.Status == RuleCheckStatus.Satisfied);
        }

        /// <summary>R16：让路船全程保向保速 → R16、R8 不满足；R15 不满足。</summary>
        [Fact]
        public void R16_NoAction_NotSatisfied()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(450), CrossTgt().Run(450));
            Assert.Equal(RuleCheckStatus.NotSatisfied, Checks(r, ColregRuleId.R16, Own).First().Status);
            Assert.Equal(RuleCheckStatus.NotSatisfied, Checks(r, ColregRuleId.R15, Own).First().Status);
            Assert.Contains(Checks(r, ColregRuleId.R8, Own), c => c.Status == RuleCheckStatus.NotSatisfied);
        }

        /// <summary>R16"大幅度"：及早但只右转 5°（小于 R8 明显阈值 10°）→ 不满足。</summary>
        [Fact]
        public void R16_SmallAlteration_NotSatisfied()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Order(60, 5).Run(450), CrossTgt().Run(450));
            Assert.DoesNotContain(Checks(r, ColregRuleId.R16, Own), c => c.Status == RuleCheckStatus.Satisfied);
        }

        // ---------- R17 ----------

        /// <summary>R17(a)(i)/(b)：直航船保向保速 → 早期 R17(a)(i) 满足；进入紧迫阶段（TCPA≤60 s）仍保向保速 → R17(b) 不满足。</summary>
        [Fact]
        public void R17_StandOnHolds_ThenFailsToActInExtremis()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(450), CrossTgt().Run(450));
            var c = Checks(r, ColregRuleId.R17, Tgt).ToList();
            Assert.Contains(c, x => x.Clause == "R17(a)(i)" && x.Status == RuleCheckStatus.Satisfied);
            Assert.Contains(c, x => x.Clause == "R17(b)" && x.Status == RuleCheckStatus.NotSatisfied);
        }

        /// <summary>R17(a)(i)：让路船尚有充分时间（TCPA≈300 s）时直航船擅自大幅右转 → 不满足保向保速。</summary>
        [Fact]
        public void R17_StandOnPrematureAlteration_NotSatisfied()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(450), CrossTgt().Order(100, 315).Run(450));
            Assert.Contains(Checks(r, ColregRuleId.R17, Tgt), x => x.Clause == "R17(a)(i)" && x.Status == RuleCheckStatus.NotSatisfied);
        }

        /// <summary>
        /// R17(a)(ii)：让路船未行动，TCPA≈175 s（已进入引擎自身的介入门限 180 s）时直航船独自右转 120° 远离，碰撞危险在 240 s 解除、驶过距离 ≥0.5 nm。
        /// 这是允许的独自行动，不应判 NotSatisfied；也不应因本船转向使 TCPA 回升而把同一操纵的后半段改按 R17(a)(i)"擅自变向"判定。
        /// </summary>
        [Fact]
        [Trait("Category", "KnownDefect")]
        public void W1_D06_R17_StandOnIndependentAction_NotFragmentedIntoViolations()
        {
            var tgt = CrossTgt();
            var r = Ok(new Ship(0, 0, 0, 5).Run(450), tgt.Order(225, Norm(tgt.Heading + 120)).Run(450));
            var during = Checks(r, ColregRuleId.R17, Tgt).Where(x => x.EndTime.Seconds > 220 && x.Status != RuleCheckStatus.NotApplicable).ToList();
            Assert.NotEmpty(during);
            Assert.DoesNotContain(during, x => x.Status == RuleCheckStatus.NotSatisfied);
        }

        /// <summary>R17(c)：交叉局面直航船若采取行动，不应对左舷来船向左转向 → 不满足。</summary>
        [Fact]
        public void R17_StandOnPortTurnTowardPortVessel_NotSatisfied()
        {
            var tgt = CrossTgt();
            var r = Ok(new Ship(0, 0, 0, 5).Run(450), tgt.Order(250, Norm(tgt.Heading - 60)).Run(450));
            Assert.Contains(Checks(r, ColregRuleId.R17, Tgt), x => x.Status == RuleCheckStatus.NotSatisfied && x.ActualAction.MaxPortTurnDeg > 30);
        }

        /// <summary>R13 + R17：被追越船（直航船）中途大幅转向，R13 对被追越船的核查应与 R17 保向保速结论一致，不应 R13=满足而 R17=不满足。</summary>
        [Fact]
        public void R13_OvertakenVesselAlteration_R13AndR17Agree()
        {
            var own = new Ship(0, 0, 0, 5).Order(30, 40);
            var r = Ok(own.Run(300), new Ship(0, -800, 0, 10).Run(300));
            var r13 = Checks(r, ColregRuleId.R13, Own).Where(c => c.Status != RuleCheckStatus.NotApplicable).ToList();
            var r17 = Checks(r, ColregRuleId.R17, Own).Where(c => c.Status != RuleCheckStatus.NotApplicable).ToList();
            Assert.NotEmpty(r13);
            Assert.Contains(r17, c => c.Status == RuleCheckStatus.NotSatisfied);
            Assert.DoesNotContain(r13, c => c.Status == RuleCheckStatus.Satisfied);
        }

        // ---------- R8 明显行动阈值 ----------

        /// <summary>
        /// R8(b)"大得足以使他船容易察觉"。复测按裁定 A5 改写（原断言以 10° 为默认）：默认 SubstantialTurnDeg=30°，
        /// 10°/25° 非明显、30° 明显（含边界）；阈值仍可配置为 10°（见下一用例）。安全距离阈值放宽以单独观察"明显"。
        /// </summary>
        [Theory]
        [InlineData(9.5, false)]
        [InlineData(10.0, false)]
        [InlineData(25.0, false)]
        [InlineData(30.0, true)]
        public void R8_SubstantialTurnThreshold(double turn, bool substantial)
        {
            var th = new ColregThresholds(safePassingDcpaNm: 0.001, clearDistanceNm: 0.001);
            var r = Ok(new Ship(0, 0, 0, 5).Order(60, turn).Run(450), CrossTgt().Run(450), th);
            var first = Checks(r, ColregRuleId.R8, Own).First();
            Assert.Contains("明显行动=" + substantial, first.Explanation);
        }

        /// <summary>A5：阈值可配置回 10°：9.5° 非明显、10° 明显（含边界）、25° 明显。</summary>
        [Theory]
        [InlineData(9.5, false)]
        [InlineData(10.0, true)]
        [InlineData(25.0, true)]
        public void R8_SubstantialTurnThreshold_ConfiguredTo10(double turn, bool substantial)
        {
            var th = new ColregThresholds(substantialTurnDeg: 10, safePassingDcpaNm: 0.001, clearDistanceNm: 0.001);
            var r = Ok(new Ship(0, 0, 0, 5).Order(60, turn).Run(450), CrossTgt().Run(450), th);
            Assert.Contains("明显行动=" + substantial, Checks(r, ColregRuleId.R8, Own).First().Explanation);
        }

        /// <summary>阈值可配置：SubstantialTurnDeg=30 时 20° 右转不再"明显"。</summary>
        [Fact]
        public void R8_SubstantialTurnThreshold_IsConfigurable()
        {
            var th = new ColregThresholds(substantialTurnDeg: 30, safePassingDcpaNm: 0.001, clearDistanceNm: 0.001);
            var r = Ok(new Ship(0, 0, 0, 5).Order(60, 20).Run(450), CrossTgt().Run(450), th);
            Assert.Contains("明显行动=False", Checks(r, ColregRuleId.R8, Own).First().Explanation);
        }

        /// <summary>R8(b) 变速代理：减速 ≥1.0 m/s 为明显行动。</summary>
        [Fact]
        public void R8_SubstantialSpeedReduction()
        {
            var th = new ColregThresholds(safePassingDcpaNm: 0.001, clearDistanceNm: 0.001);
            var r = Ok(new Ship(0, 0, 0, 5) { Accel = 5 }.Order(60, 0, 2.0).Run(450), CrossTgt().Run(450), th);
            Assert.Contains("明显行动=True", Checks(r, ColregRuleId.R8, Own).First().Explanation);
        }

        /// <summary>359°→1° 跨零小幅右转：本船 355°→15°（+20°）应识别为右转 20°，不得为 -340°。</summary>
        [Fact]
        public void HeadingWrap_TurnAcrossNorth_IsStarboard20()
        {
            var r = Ok(new Ship(0, 0, 355, 5).Order(60, 15).Run(300), new Ship(0, 4000, 175, 5).Run(300));
            var c = Checks(r, ColregRuleId.R8, Own).First();
            var all = r.RuleChecks.Where(x => x.VesselId == Own).Select(x => x.ActualAction.HeadingChangeDeg).ToList();
            Assert.Contains(all, h => System.Math.Abs(h - 20) < 0.5);
            Assert.DoesNotContain(all, h => System.Math.Abs(h) > 25);
            Assert.Equal(TurnDirection.Starboard, r.RuleChecks.First(x => x.VesselId == Own && System.Math.Abs(x.ActualAction.HeadingChangeDeg - 20) < 0.5).ActualAction.Turn);
        }

        // ---------- R19(d) ----------

        /// <summary>R19(d)(i)：能见度不良、对正横前且构成碰撞危险的他船，本船左转 → 不满足。</summary>
        [Fact]
        public void R19d_i_PortTurnForVesselForwardOfBeam_NotSatisfied()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Order(60, 330).Run(300), CollisionTarget(0, 4000, 400).Run(300), vis: 0.5, inSight: false);
            Assert.Contains(Checks(r, ColregRuleId.R19, Own), c => c.Clause == "R19(d)(i)" && c.Status == RuleCheckStatus.NotSatisfied);
        }

        /// <summary>R19(d)(i)：右转避让正前方来船 → 满足（不违反）。</summary>
        [Fact]
        public void R19d_i_StarboardTurnForVesselAhead_Satisfied()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Order(60, 40).Run(300), CollisionTarget(0, 4000, 400).Run(300), vis: 0.5, inSight: false);
            Assert.Contains(Checks(r, ColregRuleId.R19, Own), c => c.Clause == "R19(d)(i)" && c.Status == RuleCheckStatus.Satisfied);
        }

        /// <summary>R19(d)(ii)：他船在右舷正横后且有碰撞危险，本船右转（朝其转向）→ 不满足。</summary>
        [Fact]
        public void R19d_ii_TurnTowardVesselAbaftBeam_NotSatisfied()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Order(30, 40).Run(200), CollisionTarget(150, 1000, 300).Run(200), vis: 0.5, inSight: false);
            Assert.Contains(Checks(r, ColregRuleId.R19, Own), c => c.Clause == "R19(d)(ii)" && c.Status == RuleCheckStatus.NotSatisfied);
        }

        /// <summary>
        /// R19(d) 的转向限制以"判定正在形成紧迫局面和/或存在碰撞危险并采取避让行动"为前提。
        /// 他船在右前方 2 nm 外安全驶过（无碰撞危险）时本船左转，不应判 R19(d)(i) 不满足。
        /// </summary>
        [Fact]
        [Trait("Category", "KnownDefect")]
        public void W1_D05_R19d_NotApplicableWithoutCloseQuartersOrRisk()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Order(30, 340).Run(200), new Ship(4000, 4000, 180, 5).Run(200), vis: 0.5, inSight: false);
            Assert.DoesNotContain(Checks(r, ColregRuleId.R19, Own), c => c.Clause.StartsWith("R19(d)") && c.Status == RuleCheckStatus.NotSatisfied);
        }

        /// <summary>
        /// R19(b) 安全航速。复测按裁定 A5 改写（原断言按 5 m/s 硬判满足/不满足）：安全航速不做硬判，
        /// 有碰撞危险/紧迫局面时一律 NeedsReview，说明列出观测航速、能见度和提示值；SafeSpeedMps 只改变"超过提示值"措辞。
        /// </summary>
        [Fact]
        public void R19b_SafeSpeedProxy_ConfigurableThreshold()
        {
            var tgt = CollisionTarget(0, 4000, 400);
            var fast = Ok(new Ship(0, 0, 0, 7).Run(200), tgt.Run(200), vis: 0.5, inSight: false);
            var f = Checks(fast, ColregRuleId.R19, Own).Where(c => c.Clause == "R19(b)" && c.Status != RuleCheckStatus.NotApplicable).ToList();
            Assert.NotEmpty(f);
            Assert.All(f, c => Assert.Equal(RuleCheckStatus.NeedsReview, c.Status));
            Assert.Contains(f, c => c.Explanation.Contains("7.000m/s") && c.Explanation.Contains("0.500nm") && c.Explanation.Contains("超过提示值"));
            var relaxed = Ok(new Ship(0, 0, 0, 7).Run(200), tgt.Run(200), new ColregThresholds(safeSpeedMps: 8), vis: 0.5, inSight: false);
            var g = Checks(relaxed, ColregRuleId.R19, Own).Where(c => c.Clause == "R19(b)" && c.Status != RuleCheckStatus.NotApplicable).ToList();
            Assert.NotEmpty(g);
            Assert.All(g, c => Assert.Equal(RuleCheckStatus.NeedsReview, c.Status));
            Assert.DoesNotContain(g, c => c.Explanation.Contains("超过提示值"));
            Assert.DoesNotContain(fast.RuleChecks.Concat(relaxed.RuleChecks), c => (c.Clause == "R19(b)" || c.Clause == "R6") &&
                (c.Status == RuleCheckStatus.Satisfied || c.Status == RuleCheckStatus.NotSatisfied));
        }
    }
}

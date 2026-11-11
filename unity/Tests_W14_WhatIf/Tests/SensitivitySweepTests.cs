using System;
using Xunit;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Demo;

namespace Mcis.Tests.W14
{
    public class SensitivitySweepTests
    {
        [Fact]
        public void TurnAdvanceHasCollisionCriticalInsideRange()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            SensitivityResult result = SensitivitySweep.SweepTurnAdvance(
                setup,
                WhatIfDemoFixture.MaryId,
                WhatIfDemoFixture.BaselineMaryTurnTimeSeconds,
                15.0, 15.0,
                0.0, 180.0, 5.0);

            Assert.Equal(37, result.Points.Count);
            Assert.True(result.CriticalValueCollision.HasValue);
            double critical = result.CriticalValueCollision.Value;
            Assert.InRange(critical, 0.0, 180.0);
            Assert.True(critical > 0.0);
            Assert.Contains("可避免碰撞", result.Description);
            Assert.Contains("≥", result.Description);

            ScenarioResult before = ScenarioEvaluator.Evaluate(
                setup, WhatIfDemoFixture.TurnAdvanceScenario(critical - 0.49));
            ScenarioResult at = ScenarioEvaluator.Evaluate(
                setup, WhatIfDemoFixture.TurnAdvanceScenario(critical));

            Assert.True(before.Collision, "临界值左侧应仍碰撞");
            Assert.False(at.Collision, "临界值右侧应不再碰撞");

            Assert.True(result.CriticalValueSafe.HasValue);
            double safeCritical = result.CriticalValueSafe.Value;
            Assert.InRange(safeCritical, 0.0, 180.0);
            ScenarioResult atSafe = ScenarioEvaluator.Evaluate(
                setup, WhatIfDemoFixture.TurnAdvanceScenario(safeCritical));
            Assert.False(atSafe.Collision);
            Assert.True(atSafe.MinClearanceM >= setup.SafeDistanceM - 1e-6,
                "安全临界值处净距应达到 0.1 nm");
        }

        [Fact]
        public void NoTransitionReturnsNullCriticalValue()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            Func<double, WhatIfScenario> factory =
                value => WhatIfScenario.Original("S0", "原始");

            SensitivityResult result = SensitivitySweep.Run(
                setup, "测试参数", "s", factory, 0.0, 20.0, 5.0, 0.5);

            Assert.Null(result.CriticalValueCollision);
            Assert.Null(result.CriticalValueSafe);
            Assert.Contains("均为碰撞", result.Description);
            Assert.Equal(5, result.Points.Count);
        }

        [Fact]
        public void AlwaysSafeSweepHasNoTransitions()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            Func<double, WhatIfScenario> factory =
                value => WhatIfDemoFixture.TurnAdvanceScenario(180.0);

            SensitivityResult result = SensitivitySweep.Run(
                setup, "转向提前量", "s", factory, 0.0, 20.0, 5.0, 0.5);

            Assert.Null(result.CriticalValueCollision);
            Assert.Null(result.CriticalValueSafe);
            Assert.Contains("均未发生碰撞", result.Description);
        }

        [Fact]
        public void SensitivityResultCarriesAssumptionsAndDisclaimer()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            SensitivityResult result = SensitivitySweep.SweepTurnAdvance(
                setup, WhatIfDemoFixture.MaryId,
                WhatIfDemoFixture.BaselineMaryTurnTimeSeconds,
                15.0, 15.0, 0.0, 60.0, 10.0);

            Assert.NotEmpty(result.Assumptions);
            Assert.Equal(WhatIfAssumptions.DisclaimerText, result.Disclaimer);
            Assert.All(result.Points, p => Assert.True(p.MinDistanceNm >= 0.0));
        }
    }
}

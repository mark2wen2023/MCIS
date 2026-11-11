using System;
using System.Collections.Generic;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Demo;
using Xunit;

namespace Mcis.Acceptance.W14
{
    public class SensitivityComparisonAcceptanceTests
    {
        [Fact]
        public void TurnAdvanceSweep_IsMonotonicAndBisectionConverges()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            SensitivityResult sweep = SensitivitySweep.SweepTurnAdvance(
                setup, WhatIfDemoFixture.MaryId,
                WhatIfDemoFixture.BaselineMaryTurnTimeSeconds,
                15.0, 15.0, 0.0, 200.0, 10.0);

            Assert.True(sweep.Points.Count >= 20);
            // 碰撞标志：一旦变为不碰撞，之后不应再回到碰撞（单调）。
            bool seenClear = false;
            for (int i = 0; i < sweep.Points.Count; i++)
            {
                if (!sweep.Points[i].Collision) seenClear = true;
                else Assert.False(seenClear, "敏感性扫描在提前量增大后再次出现碰撞，不单调。参数=" +
                    sweep.Points[i].ParameterValue);
            }

            Assert.True(sweep.CriticalValueCollision.HasValue);
            Assert.InRange(sweep.CriticalValueCollision.Value, 20.0, 80.0);
            // 实施方自报 36.6 s；允许 2 s 容差核对数字。
            Assert.InRange(sweep.CriticalValueCollision.Value, 34.6, 38.6);

            ScenarioResult justBelow = ScenarioEvaluator.Evaluate(
                setup, WhatIfDemoFixture.TurnAdvanceScenario(sweep.CriticalValueCollision.Value - 0.6));
            ScenarioResult justAt = ScenarioEvaluator.Evaluate(
                setup, WhatIfDemoFixture.TurnAdvanceScenario(sweep.CriticalValueCollision.Value));
            Assert.True(justBelow.Collision, "临界值左侧应仍碰撞");
            Assert.False(justAt.Collision, "临界值处应已避免碰撞（二分返回 hi）");

            Assert.True(sweep.CriticalValueSafe.HasValue);
            Assert.InRange(sweep.CriticalValueSafe.Value, 150.0, 200.0);
            // 独立 Python（全程真实净距 + 二分）得到 171.11 s；产品二分容差默认 0.5 s，
            // C# 报 171.25 s，差值 0.14 s 落在容差内，不记缺陷。窗口按独立值 ±0.5 s 调整。
            Assert.InRange(sweep.CriticalValueSafe.Value, 170.61, 171.61);

            ScenarioResult atSafe = ScenarioEvaluator.Evaluate(
                setup, WhatIfDemoFixture.TurnAdvanceScenario(sweep.CriticalValueSafe.Value));
            Assert.False(atSafe.Collision);
            Assert.True(atSafe.MinClearanceM + 1e-6 >= setup.SafeDistanceM,
                "安全临界值处净距应达到安全线，实际 " + atSafe.MinClearanceM + " / " + setup.SafeDistanceM);

            Assert.Equal(WhatIfAssumptions.DisclaimerText, sweep.Disclaimer);
            Assert.Contains("仅供分析参考", sweep.Disclaimer);
            Assert.NotEmpty(sweep.Assumptions);
        }

        [Fact]
        public void ComparisonTable_HasAllColumnsSourcesAndDisclaimer()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<ScenarioResult> results = ScenarioEvaluator.EvaluateAll(setup, WhatIfDemoFixture.Scenarios());
            ComparisonTable table = ScenarioComparison.Build(results);

            Assert.Equal(4, table.Rows.Count);
            Assert.Equal("S0", table.Rows[0].ScenarioId);
            Assert.Equal(0.0, table.Rows[0].DeltaMinDistanceNm, 9);
            Assert.Equal(WhatIfAssumptions.DisclaimerText, table.Disclaimer);
            Assert.Contains("仅供分析参考", table.Disclaimer);
            Assert.NotEmpty(table.Assumptions);
            Assert.NotEmpty(table.Inputs);
            Assert.All(table.Inputs, v =>
            {
                Assert.False(string.IsNullOrWhiteSpace(v.Name));
                Assert.False(string.IsNullOrWhiteSpace(v.Reference));
                Assert.True(Enum.IsDefined(typeof(ValueSource), v.Source));
            });
            Assert.Contains(table.Inputs, v => v.Source == ValueSource.Fictional);

            string md = table.ToMarkdown();
            Assert.Contains("最小距离", md);
            Assert.Contains("碰撞角", md);
            Assert.Contains("接触部位", md);
            Assert.Contains("偏离后最小DCPA", md);
            Assert.Contains("模型假设", md);
            Assert.Contains("免责声明", md);
            Assert.Contains(WhatIfAssumptions.DisclaimerText, md);
        }

        [Fact]
        public void ComparisonRequiresS0()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<WhatIfScenario> all = WhatIfDemoFixture.Scenarios();
            ScenarioResult s1 = ScenarioEvaluator.Evaluate(setup, all[1]);
            Assert.Throws<ArgumentException>(() => ScenarioComparison.Build(new[] { s1 }));
        }

        [Fact]
        public void EveryDemoResult_CarriesDisclaimerAssumptionsAndSourcedInputs()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<ScenarioResult> results = ScenarioEvaluator.EvaluateAll(setup, WhatIfDemoFixture.Scenarios());
            Assert.All(results, r =>
            {
                Assert.Equal(WhatIfAssumptions.DisclaimerText, r.Disclaimer);
                Assert.Contains("仅供分析参考", r.Disclaimer);
                Assert.NotEmpty(r.Assumptions);
                Assert.Contains(r.Assumptions, a => a.Contains("Nomoto"));
                Assert.NotEmpty(r.Inputs);
                Assert.All(r.Inputs, v =>
                {
                    Assert.False(string.IsNullOrWhiteSpace(v.Reference));
                    Assert.Equal(ValueSource.Fictional, v.Source);
                });
            });
        }

        [Fact]
        public void MinDcpa_IsGlobalMinimum_SameBeforeIntervention()
        {
            // 确认实施方已知问题：最小 DCPA 取全时段，干预前各情景相同。
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<ScenarioResult> results = ScenarioEvaluator.EvaluateAll(setup, WhatIfDemoFixture.Scenarios());
            ScenarioResult s0 = results[0];
            ScenarioResult s1 = results[1];
            ScenarioResult s3 = results[3];
            Assert.Equal(s0.MinDcpaNm, s1.MinDcpaNm, 6);
            Assert.Equal(s0.MinDcpaNm, s3.MinDcpaNm, 6);
            Assert.InRange(s0.MinDcpaNm, 0.0, 0.05);
        }
    }
}

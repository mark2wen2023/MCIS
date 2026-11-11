using System;
using System.Collections.Generic;
using Xunit;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Demo;

namespace Mcis.Tests.W14
{
    public class ScenarioComparisonTests
    {
        [Fact]
        public void ComparisonHasFourRowsAndS0DeltaIsZero()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<ScenarioResult> results =
                ScenarioEvaluator.EvaluateAll(setup, WhatIfDemoFixture.Scenarios());
            ComparisonTable table = ScenarioComparison.Build(results);

            Assert.Equal(4, table.Rows.Count);
            Assert.Equal("S0", table.Rows[0].ScenarioId);
            Assert.Equal(0.0, table.Rows[0].DeltaMinDistanceNm);
            for (int i = 1; i < table.Rows.Count; i++)
            {
                Assert.Equal(
                    table.Rows[i].MinDistanceNm - table.Rows[0].MinDistanceNm,
                    table.Rows[i].DeltaMinDistanceNm);
            }
        }

        [Fact]
        public void MarkdownContainsHeaderRowsAssumptionsAndDisclaimer()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<ScenarioResult> results =
                ScenarioEvaluator.EvaluateAll(setup, WhatIfDemoFixture.Scenarios());
            string markdown = ScenarioComparison.Build(results).ToMarkdown();

            Assert.Contains("| 情景 | 改动 | 最小距离(nm) | 最小净距(m) | 最小DCPA(nm) | 碰撞时刻 | 结论 |", markdown);
            Assert.Contains("| S0 |", markdown);
            Assert.Contains("| S1 |", markdown);
            Assert.Contains("| S2 |", markdown);
            Assert.Contains("| S3 |", markdown);
            Assert.Contains("模型假设", markdown);
            Assert.Contains(WhatIfAssumptions.DisclaimerText, markdown);
        }

        [Fact]
        public void MissingS0ThrowsArgumentException()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            ScenarioResult s1 = ScenarioEvaluator.Evaluate(setup, WhatIfDemoFixture.Scenarios()[1]);

            Assert.Throws<ArgumentException>(() => ScenarioComparison.Build(new[] { s1 }));
        }

        [Fact]
        public void ComparisonTableCarriesAssumptionsAndDisclaimer()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            ComparisonTable table = ScenarioComparison.Build(
                ScenarioEvaluator.EvaluateAll(setup, WhatIfDemoFixture.Scenarios()));

            Assert.NotEmpty(table.Assumptions);
            Assert.Equal(WhatIfAssumptions.DisclaimerText, table.Disclaimer);
        }
    }
}

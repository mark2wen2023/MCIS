using System;
using System.Collections.Generic;
using Xunit;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Demo;

namespace Mcis.Tests.W14
{
    public class SourcedValueTests
    {
        [Fact]
        public void SourceTextCoversAllClassifications()
        {
            Assert.Equal("报告直接", Value(new SourcedValue("a", 1.0, "m", ValueSource.ReportDirect, "r")).SourceText);
            Assert.Equal("推算", Value(new SourcedValue("b", 2.0, "m", ValueSource.ReportDerived, "r")).SourceText);
            Assert.Equal("估计", Value(new SourcedValue("c", 3.0, "m", ValueSource.Estimated, "r")).SourceText);
            Assert.Equal("虚构示例", Value(new SourcedValue("d", 4.0, "m", ValueSource.Fictional, "r")).SourceText);
        }

        [Fact]
        public void ConstructorRejectsMissingNameReferenceAndNonFiniteValue()
        {
            Assert.Throws<ArgumentException>(() =>
                new SourcedValue(" ", 1.0, "m", ValueSource.Estimated, "r"));
            Assert.Throws<ArgumentException>(() =>
                new SourcedValue("a", 1.0, "m", ValueSource.Estimated, " "));
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                new SourcedValue("a", double.NaN, "m", ValueSource.Estimated, "r"));
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                new SourcedValue("a", double.PositiveInfinity, "m", ValueSource.Estimated, "r"));
        }

        [Fact]
        public void DemoResultAndComparisonCarryFictionalInputs()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            ScenarioResult s0 = ScenarioEvaluator.Evaluate(setup, WhatIfDemoFixture.Scenarios()[0]);

            Assert.Contains(s0.Assumptions, a => a.Contains("虚构示例数据"));
            Assert.Equal(6, s0.Inputs.Count);
            Assert.All(s0.Inputs, value =>
            {
                Assert.False(string.IsNullOrWhiteSpace(value.Reference));
                Assert.Equal(ValueSource.Fictional, value.Source);
                Assert.Equal("虚构示例", value.SourceText);
            });

            ComparisonTable table = ScenarioComparison.Build(
                ScenarioEvaluator.EvaluateAll(setup, WhatIfDemoFixture.Scenarios()));
            Assert.Equal(6, table.Inputs.Count);
            Assert.All(table.Inputs, value => Assert.False(string.IsNullOrWhiteSpace(value.Reference)));
        }

        [Fact]
        public void ScenarioSpecificInputsAreMergedIntoResult()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            SourcedValue scenarioValue = new SourcedValue(
                "测试情景输入", 42.0, "s", ValueSource.ReportDerived, "测试引用", "测试说明");
            VesselScenario vessel = VesselScenario.Create(
                WhatIfDemoFixture.MaryId,
                Intervention.TurnStarboard(420.0, 15.0, 15.0));
            WhatIfScenario scenario = new WhatIfScenario(
                "SX", "测试", "测试", new[] { vessel }, new[] { scenarioValue });

            ScenarioResult result = ScenarioEvaluator.Evaluate(setup, scenario);

            Assert.Equal(7, result.Inputs.Count);
            Assert.Contains(result.Inputs, value => value.Name == "测试情景输入");
        }

        private static SourcedValue Value(SourcedValue value)
        {
            return value;
        }
    }
}

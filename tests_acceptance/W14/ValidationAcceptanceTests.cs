using System;
using System.Collections.Generic;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Demo;
using Xunit;

namespace Mcis.Acceptance.W14
{
    public class ValidationAcceptanceTests
    {
        [Fact]
        public void ManeuverParams_RejectsNaNNegativeAndOutOfRange()
        {
            Assert.Contains(new ManeuverParams(double.NaN, 60, 12).Validate(), e => e.Contains("K"));
            Assert.Contains(new ManeuverParams(-0.1, 60, 12).Validate(), e => e.Contains("K"));
            Assert.Contains(new ManeuverParams(0.1, double.NegativeInfinity, 12).Validate(), e => e.Contains("T"));
            Assert.Contains(new ManeuverParams(0.1, 0.0, 12).Validate(), e => e.Contains("T"));
            Assert.Contains(new ManeuverParams(0.1, 60, -3).Validate(), e => e.Contains("参考航速"));
            Assert.Contains(new ManeuverParams(0.1, 60, 12, maxRudderDeg: 0.0).Validate(), e => e.Contains("最大舵角"));
            Assert.Contains(new ManeuverParams(0.1, 60, 12, maxRudderDeg: 90.1).Validate(), e => e.Contains("最大舵角"));
            Assert.Contains(new ManeuverParams(0.1, 60, 12, rudderRateDegPerSec: -1).Validate(), e => e.Contains("舵机速率"));
            Assert.Contains(new ManeuverParams(0.1, 60, 12, speedTimeConstantSec: 0).Validate(), e => e.Contains("常规变速"));
            Assert.Contains(new ManeuverParams(0.1, 60, 12, stopTimeConstantSec: double.NaN).Validate(), e => e.Contains("停车"));
            Assert.Contains(new ManeuverParams(0.1, 60, 12, asternTimeConstantSec: -5).Validate(), e => e.Contains("全速后退"));
            Assert.Contains(new ManeuverParams(0.1, 60, 12, minSpeedKn: -0.01).Validate(), e => e.Contains("最低航速"));
            Assert.Contains(new ManeuverParams(0.1, 60, 12, loaM: 0).Validate(), e => e.Contains("LOA"));
            Assert.Contains(new ManeuverParams(0.1, 60, 12, beamM: -2).Validate(), e => e.Contains("型宽"));
            Assert.Contains(new ManeuverParams(0.1, 60, 12, displacementTons: 0).Validate(), e => e.Contains("排水量"));
            Assert.Empty(ManeuverParams.Default(120, 20, 9000).Validate());
        }

        [Fact]
        public void AnchorParams_RejectsNaNAndNonPositiveLimits()
        {
            Assert.Contains(new AnchorParams(-1, 0.08, 0.3, 6).Validate(), e => e.Contains("抓底时间"));
            Assert.Contains(new AnchorParams(12, double.NaN, 0.3, 6).Validate(), e => e.Contains("减速度"));
            Assert.Contains(new AnchorParams(12, 0.08, double.PositiveInfinity, 6).Validate(), e => e.Contains("转首率"));
            Assert.Contains(new AnchorParams(12, 0.08, 0.3, 0.0).Validate(), e => e.Contains("航速上限"));
            Assert.Empty(new AnchorParams().Validate());
        }

        [Fact]
        public void NomotoSimulator_RejectsInvalidStepAndInvalidParams()
        {
            KinematicState initial = new KinematicState(0, 0, 0, 0, 8);
            ManeuverParams ok = ManeuverParams.Default(100, 16, 5000);
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                NomotoSimulator.Simulate(initial, ok, Array.Empty<Intervention>(), 10, 0.0));
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                NomotoSimulator.Simulate(initial, ok, Array.Empty<Intervention>(), 10, double.NaN));
            Assert.Throws<ArgumentException>(() =>
                NomotoSimulator.Simulate(initial, new ManeuverParams(-1, 60, 12), Array.Empty<Intervention>(), 10, 0.1));
        }

        [Fact]
        public void WhatIfSetup_RejectsBadRangeAndSameVessel()
        {
            WhatIfVessel a = W14AccFixture.StraightVessel("A", 0, 0, 0, 8, 100, 16);
            WhatIfVessel b = W14AccFixture.StraightVessel("B", 200, 2000, 180, 8, 100, 16);
            Assert.Throws<ArgumentException>(() =>
                new WhatIfSetup(new[] { a, b }, "A", "A", 0, 100));
            Assert.Throws<ArgumentException>(() =>
                new WhatIfSetup(new[] { a, b }, "A", "B", 100, 100));
            Assert.Throws<ArgumentException>(() =>
                new WhatIfSetup(new[] { a, b }, "A", "B", double.NaN, 100));
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                new WhatIfSetup(new[] { a, b }, "A", "B", 0, 100, cpaStepSeconds: -1));
            Assert.Throws<ArgumentException>(() =>
                new WhatIfSetup(new[] { a, b }, "C", "B", 0, 100));
        }

        [Fact]
        public void ChangeSpeed_RejectsNegativeOrNaNTarget()
        {
            Assert.Throws<ArgumentOutOfRangeException>(() => Intervention.ChangeSpeed(10, -1));
            Assert.Throws<ArgumentOutOfRangeException>(() => Intervention.ChangeSpeed(10, double.NaN));
        }

        [Fact]
        public void SourcedValue_RejectsEmptyNameReferenceAndNonFinite()
        {
            Assert.Throws<ArgumentException>(() =>
                new SourcedValue("", 1, "m", ValueSource.Estimated, "ref"));
            Assert.Throws<ArgumentException>(() =>
                new SourcedValue("K", 1, "1/s", ValueSource.Estimated, "  "));
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                new SourcedValue("K", double.NaN, "1/s", ValueSource.Estimated, "ref"));
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                new SourcedValue("K", double.PositiveInfinity, "1/s", ValueSource.Estimated, "ref"));
        }

        [Fact]
        public void CounterfactualBuilder_RejectsNonPositiveStep()
        {
            WhatIfVessel vessel = WhatIfDemoFixture.CreateMary();
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                CounterfactualBuilder.Build(vessel, null, 0.0));
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                CounterfactualBuilder.Build(vessel, null, double.NaN));
        }

        [Fact]
        public void SensitivitySweep_RejectsBadRange()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            Func<double, WhatIfScenario> factory = WhatIfDemoFixture.TurnAdvanceScenario;
            Assert.Throws<ArgumentException>(() =>
                SensitivitySweep.Run(setup, "p", "s", factory, 10, 0, 1));
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                SensitivitySweep.Run(setup, "p", "s", factory, 0, 10, 0));
            Assert.Throws<ArgumentOutOfRangeException>(() =>
                SensitivitySweep.Run(setup, "p", "s", factory, 0, 10, 1, 0));
        }

        [Fact]
        public void Evaluate_UnknownVesselThrows()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            WhatIfScenario bad = new WhatIfScenario(
                "BAD", "未知船", "引用不存在的船",
                new[] { VesselScenario.Create("Ghost", Intervention.Stop(10)) });
            Assert.Throws<ArgumentException>(() => ScenarioEvaluator.Evaluate(setup, bad));
        }
    }
}

using System.Collections.Generic;
using System.Linq;
using Xunit;
using Mcis.Simulation.WhatIf;

namespace Mcis.Tests.W14
{
    public class ManeuverParamsTests
    {
        [Fact]
        public void ValidParametersHaveNoErrors()
        {
            ManeuverParams parameters = TestUtil.Params();
            IReadOnlyList<string> errors = parameters.Validate();
            Assert.Empty(errors);
        }

        [Fact]
        public void InvalidParametersReportChineseErrors()
        {
            ManeuverParams parameters = new ManeuverParams(
                -1.0, 0.0, 0.0, 100.0, 0.0, 0.0, 0.0, 0.0, -2.0, 0.0, -1.0, 0.0);
            IReadOnlyList<string> errors = parameters.Validate();

            Assert.True(errors.Count >= 8);
            Assert.Contains(errors, e => e.Contains("K"));
            Assert.Contains(errors, e => e.Contains("T"));
            Assert.Contains(errors, e => e.Contains("最大舵角"));
            Assert.Contains(errors, e => e.Contains("最低航速"));
            Assert.Contains(errors, e => e.Contains("LOA"));
        }

        [Fact]
        public void DefaultUsesShipDimensionsAndPositiveCoefficients()
        {
            ManeuverParams parameters = ManeuverParams.Default(120.0, 20.0, 9000.0);

            Assert.Equal(120.0, parameters.LoaM);
            Assert.Equal(20.0, parameters.BeamM);
            Assert.Equal(9000.0, parameters.DisplacementTons);
            Assert.Equal(0.10, parameters.K);
            Assert.Equal(60.0, parameters.T);
            Assert.Equal(12.0, parameters.ReferenceSpeedKn);
            Assert.Equal(35.0, parameters.MaxRudderDeg);
            Assert.Equal(2.5, parameters.RudderRateDegPerSec);
            Assert.True(parameters.AsternTimeConstantSec < parameters.StopTimeConstantSec);
            Assert.Empty(parameters.Validate());
        }

        [Fact]
        public void InterventionFactoriesApplySignsAndDelays()
        {
            Intervention starboard = Intervention.TurnStarboard(10.0, 15.0, 30.0, 2.0);
            Assert.Equal(15.0, starboard.RudderDeg);
            Assert.Equal(30.0, starboard.HeadingChangeDeg);
            Assert.Equal(12.0, starboard.ExecutionTimeSeconds);

            Intervention port = Intervention.TurnPort(10.0, 15.0, 30.0);
            Assert.Equal(-15.0, port.RudderDeg);
            Assert.Equal(-30.0, port.HeadingChangeDeg);

            Intervention speed = Intervention.ChangeSpeed(5.0, 6.0);
            Assert.Equal(InterventionKind.SpeedChange, speed.Kind);
            Assert.Equal(6.0, speed.TargetSpeedKn);

            Assert.Equal(InterventionKind.Stop, Intervention.Stop(1.0).Kind);
            Assert.Equal(InterventionKind.FullAstern, Intervention.FullAstern(1.0).Kind);
            Assert.Equal(InterventionKind.HoldCourse, Intervention.HoldCourse(1.0).Kind);
        }

        [Fact]
        public void ScenarioKeepsVesselsAndCopiesInterventions()
        {
            Intervention intervention = Intervention.TurnStarboard(100.0, 15.0, 15.0);
            VesselScenario vessel = VesselScenario.Create("Mary", intervention);
            WhatIfScenario scenario = new WhatIfScenario(
                "S1", "测试", "右转", new[] { vessel });

            Assert.Equal("S1", scenario.Id);
            Assert.Single(scenario.Vessels);
            Assert.Same(vessel, scenario.FindVessel("Mary"));
            Assert.Null(scenario.FindVessel("Lily"));
            Assert.Single(vessel.Interventions);
        }
    }
}

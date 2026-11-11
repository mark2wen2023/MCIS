using System;
using System.Collections.Generic;
using Xunit;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;
using Mcis.Simulation.WhatIf;

namespace Mcis.Tests.W14
{
    public class CounterfactualBuilderTests
    {
        [Fact]
        public void FromStatesInterpolatesHeadingAcrossNorth()
        {
            ManeuverParams parameters = TestUtil.Params();
            KinematicState[] states =
            {
                new KinematicState(0.0, 0.0, 0.0, 350.0, 8.0),
                new KinematicState(10.0, 100.0, 0.0, 10.0, 8.0)
            };
            WhatIfVessel vessel = WhatIfVessel.FromStates("M", parameters, states);

            TestUtil.AssertNear(0.0, vessel.SampleAt(5.0).HeadingDeg, 1e-9);
            TestUtil.AssertNear(355.0, vessel.SampleAt(2.5).HeadingDeg, 1e-9);
            TestUtil.AssertNear(5.0, vessel.SampleAt(7.5).HeadingDeg, 1e-9);
            TestUtil.AssertNear(50.0, vessel.SampleAt(5.0).EastM, 1e-9);
        }

        [Fact]
        public void FromStatesClampsOutsideRange()
        {
            ManeuverParams parameters = TestUtil.Params();
            WhatIfVessel vessel = WhatIfVessel.FromStates(
                "M", parameters,
                new[]
                {
                    new KinematicState(0.0, 10.0, 20.0, 350.0, 8.0),
                    new KinematicState(10.0, 110.0, 20.0, 10.0, 6.0)
                });

            KinematicState before = vessel.SampleAt(-5.0);
            KinematicState after = vessel.SampleAt(15.0);

            TestUtil.AssertNear(10.0, before.EastM, 1e-9);
            TestUtil.AssertNear(350.0, before.HeadingDeg, 1e-9);
            TestUtil.AssertNear(-5.0, before.TimeSeconds, 1e-12);
            TestUtil.AssertNear(110.0, after.EastM, 1e-9);
            TestUtil.AssertNear(10.0, after.HeadingDeg, 1e-9);
            TestUtil.AssertNear(15.0, after.TimeSeconds, 1e-12);
        }

        [Fact]
        public void FromStatesRejectsDuplicateTimestamps()
        {
            ManeuverParams parameters = TestUtil.Params();
            Assert.Throws<ArgumentException>(() => WhatIfVessel.FromStates(
                "M", parameters,
                new[]
                {
                    new KinematicState(0.0, 0.0, 0.0, 0.0, 8.0),
                    new KinematicState(0.0, 10.0, 0.0, 0.0, 8.0)
                }));
        }

        [Fact]
        public void FromShipTrackUsesEnuHeadingAndSog()
        {
            TrackSample first = new TrackSample(
                new SimTime(0.0), new GeoCoord(121.0, 31.0),
                new EnuPosition(0.0, 0.0), new Double2(10.0, 0.0),
                10.0f, 90.0f, 90.0f, 0.0f,
                SampleProvenance.Measured, TimeQuality.ExactTagBlock, false);
            TrackSample second = new TrackSample(
                new SimTime(10.0), new GeoCoord(121.001, 31.0),
                new EnuPosition(100.0, 0.0), new Double2(10.0, 0.0),
                10.0f, 90.0f, 90.0f, 0.0f,
                SampleProvenance.Measured, TimeQuality.ExactTagBlock, false);
            ShipTrack track = new ShipTrack(
                "T", new[] { first, second }, null, null, InterpolationMode.Linear);

            WhatIfVessel vessel = WhatIfVessel.FromShipTrack("T", TestUtil.Params(), track);
            KinematicState middle = vessel.SampleAt(5.0);

            Assert.Equal(0.0, vessel.StartSeconds);
            Assert.Equal(10.0, vessel.EndSeconds);
            TestUtil.AssertNear(50.0, middle.EastM, 1e-6);
            TestUtil.AssertNear(90.0, middle.HeadingDeg, 1e-6);
            TestUtil.AssertNear(TestUtil.MpsToKnots(10.0), middle.SpeedKn, 1e-6);
        }

        [Fact]
        public void BeforeDivergenceSamplesExactlyEqualOriginal()
        {
            ManeuverParams parameters = TestUtil.Params();
            WhatIfVessel vessel = BuildStraightVessel(parameters);
            VesselScenario scenario = VesselScenario.Create(
                "M", Intervention.TurnStarboard(50.0, 15.0, 10.0));

            CounterfactualTrack track = CounterfactualBuilder.Build(vessel, scenario, 0.1);

            Assert.True(track.Diverged);
            Assert.Equal(50.0, track.DivergeTimeSeconds);
            double[] times = { 0.0, 10.0, 25.0, 49.9, 50.0 };
            for (int i = 0; i < times.Length; i++)
            {
                Assert.Equal(vessel.Original(times[i]), track.SampleAt(times[i]));
            }
        }

        [Fact]
        public void EarlierDivergeTimeHoldsCourseAndSpeedUntilIntervention()
        {
            ManeuverParams parameters = TestUtil.Params();
            WhatIfVessel vessel = WhatIfVessel.FromStates(
                "M", parameters,
                new[]
                {
                    new KinematicState(0.0, 0.0, 0.0, 0.0, 8.0),
                    new KinematicState(50.0, 0.0, 400.0, 30.0, 8.0)
                });
            VesselScenario scenario = new VesselScenario(
                "M", 10.0,
                new[] { Intervention.TurnStarboard(60.0, 20.0, 10.0) });

            CounterfactualTrack track = CounterfactualBuilder.Build(vessel, scenario, 0.1);
            KinematicState held = track.SampleAt(30.0);
            KinematicState original = vessel.SampleAt(30.0);

            TestUtil.AssertNear(6.0, held.HeadingDeg, 0.01);
            TestUtil.AssertNear(8.0, held.SpeedKn, 1e-6);
            Assert.True(TestUtil.HeadingDifference(original.HeadingDeg, held.HeadingDeg) > 5.0);
            Assert.Equal(10.0, track.DivergeTimeSeconds);
        }

        [Fact]
        public void NullScenarioEqualsOriginalTrack()
        {
            ManeuverParams parameters = TestUtil.Params();
            WhatIfVessel vessel = BuildStraightVessel(parameters);

            CounterfactualTrack track = CounterfactualBuilder.Build(vessel, null, 0.1);

            Assert.False(track.Diverged);
            Assert.True(double.IsNaN(track.DivergeTimeSeconds));
            for (double t = 0.0; t <= 100.0; t += 7.3)
            {
                Assert.Equal(vessel.Original(t), track.SampleAt(t));
            }
        }

        [Fact]
        public void SimulationIsBitwiseDeterministic()
        {
            ManeuverParams parameters = TestUtil.Params();
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 0.0, 8.0);
            Intervention[] interventions =
            {
                Intervention.TurnStarboard(5.0, 15.0, 20.0, 1.0),
                Intervention.ChangeSpeed(30.0, 6.0)
            };

            IReadOnlyList<KinematicState> first = NomotoSimulator.Simulate(
                initial, parameters, interventions, 120.0, 0.1);
            IReadOnlyList<KinematicState> second = NomotoSimulator.Simulate(
                initial, parameters, interventions, 120.0, 0.1);

            Assert.Equal(first.Count, second.Count);
            for (int i = 0; i < first.Count; i++)
            {
                Assert.Equal(first[i], second[i]);
            }
        }

        private static WhatIfVessel BuildStraightVessel(ManeuverParams parameters)
        {
            List<KinematicState> states = new List<KinematicState>();
            for (int i = 0; i <= 100; i++)
            {
                states.Add(new KinematicState(i, 0.0, i * 4.0, 0.0, 8.0));
            }
            return WhatIfVessel.FromStates("M", parameters, states);
        }
    }
}

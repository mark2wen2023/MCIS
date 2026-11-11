using System;
using System.Collections.Generic;
using Xunit;
using Mcis.Simulation.WhatIf;

namespace Mcis.Tests.W14
{
    public class EmergencyAnchorTests
    {
        [Fact]
        public void AnchorFactoryCarriesSideAndLabel()
        {
            Intervention anchor = Intervention.EmergencyAnchor(12.0, AnchorSide.Port, 1.5);

            Assert.Equal(InterventionKind.EmergencyAnchor, anchor.Kind);
            Assert.Equal(AnchorSide.Port, anchor.AnchorSide);
            Assert.Equal(13.5, anchor.ExecutionTimeSeconds);
            Assert.Contains("左舷", anchor.Label);
            Assert.NotEqual(InterventionKind.FullAstern, anchor.Kind);
        }

        [Fact]
        public void DefaultAnchorParamsAreEstimatedAndValid()
        {
            AnchorParams anchor = AnchorParams.Default(70000.0);

            Assert.Equal(12.0, anchor.LetGoToBiteSec);
            Assert.True(anchor.DecelerationKnPerSec > 0.0);
            Assert.True(anchor.YawRateDegPerSec > 0.0);
            Assert.True(anchor.MaxEffectiveSpeedKn > 0.0);
            Assert.Empty(anchor.Validate());
        }

        [Fact]
        public void AnchorValidationRejectsNegativeValues()
        {
            AnchorParams anchor = new AnchorParams(-1.0, -1.0, -1.0, 0.0);
            Assert.Equal(4, anchor.Validate().Count);
        }

        [Fact]
        public void BeforeBiteAnchorMatchesNoAnchorBitwise()
        {
            AnchorParams anchor = new AnchorParams(10.0, 0.5, 1.0, 20.0);
            ManeuverParams parameters = TestUtil.Params(anchor: anchor);
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 0.0, 10.0);

            IReadOnlyList<KinematicState> withAnchor = NomotoSimulator.Simulate(
                initial, parameters,
                new[] { Intervention.EmergencyAnchor(0.0, AnchorSide.Starboard) },
                10.0, 0.05);
            IReadOnlyList<KinematicState> withoutAnchor = NomotoSimulator.Simulate(
                initial, parameters, Array.Empty<Intervention>(), 10.0, 0.05);

            Assert.Equal(withoutAnchor.Count, withAnchor.Count);
            for (int i = 0; i < withAnchor.Count; i++)
            {
                Assert.Equal(withoutAnchor[i], withAnchor[i]);
            }
        }

        [Fact]
        public void AfterBiteAnchorDeceleratesFasterThanNoAnchor()
        {
            AnchorParams anchor = new AnchorParams(0.0, 0.5, 0.0, 20.0);
            ManeuverParams parameters = TestUtil.Params(anchor: anchor);
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 0.0, 10.0);

            IReadOnlyList<KinematicState> withAnchor = NomotoSimulator.Simulate(
                initial, parameters,
                new[] { Intervention.EmergencyAnchor(0.0, AnchorSide.Both) },
                20.0, 0.05);
            IReadOnlyList<KinematicState> withoutAnchor = NomotoSimulator.Simulate(
                initial, parameters, Array.Empty<Intervention>(), 20.0, 0.05);

            Assert.True(TestUtil.LastState(withAnchor).SpeedKn <
                        TestUtil.LastState(withoutAnchor).SpeedKn - 5.0);
        }

        [Fact]
        public void StarboardAndPortAnchorYawInOppositeDirections()
        {
            AnchorParams anchor = new AnchorParams(0.0, 0.0, 1.0, 100.0);
            ManeuverParams parameters = TestUtil.Params(anchor: anchor);
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 90.0, 10.0);

            IReadOnlyList<KinematicState> starboard = NomotoSimulator.Simulate(
                initial, parameters,
                new[] { Intervention.EmergencyAnchor(0.0, AnchorSide.Starboard) },
                10.0, 0.05);
            IReadOnlyList<KinematicState> port = NomotoSimulator.Simulate(
                initial, parameters,
                new[] { Intervention.EmergencyAnchor(0.0, AnchorSide.Port) },
                10.0, 0.05);

            Assert.True(SignedHeadingDelta(TestUtil.LastState(starboard).HeadingDeg, 90.0) > 5.0,
                "右舷锚应使船首向右偏转");
            Assert.True(SignedHeadingDelta(TestUtil.LastState(port).HeadingDeg, 90.0) < -5.0,
                "左舷锚应使船首向左偏转");
        }

        [Fact]
        public void BothAnchorDoesNotYaw()
        {
            AnchorParams anchor = new AnchorParams(0.0, 0.0, 1.0, 100.0);
            ManeuverParams parameters = TestUtil.Params(anchor: anchor);
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 90.0, 10.0);

            IReadOnlyList<KinematicState> both = NomotoSimulator.Simulate(
                initial, parameters,
                new[] { Intervention.EmergencyAnchor(0.0, AnchorSide.Both) },
                10.0, 0.05);

            TestUtil.AssertNear(90.0, TestUtil.LastState(both).HeadingDeg, 1e-9);
        }

        [Fact]
        public void AnchorStacksWithFullAsternForFasterDeceleration()
        {
            AnchorParams anchor = new AnchorParams(0.0, 0.5, 0.0, 20.0);
            ManeuverParams parameters = TestUtil.Params(asternTau: 30.0, anchor: anchor);
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 0.0, 10.0);

            IReadOnlyList<KinematicState> asternOnly = NomotoSimulator.Simulate(
                initial, parameters,
                new[] { Intervention.FullAstern(0.0) }, 30.0, 0.05);
            IReadOnlyList<KinematicState> asternAndAnchor = NomotoSimulator.Simulate(
                initial, parameters,
                new[]
                {
                    Intervention.FullAstern(0.0),
                    Intervention.EmergencyAnchor(0.0, AnchorSide.Both)
                },
                30.0, 0.05);

            Assert.True(TestUtil.LastState(asternAndAnchor).SpeedKn <
                        TestUtil.LastState(asternOnly).SpeedKn);
        }

        [Fact]
        public void SpeedNeverFallsBelowMinimumWithAnchor()
        {
            AnchorParams anchor = new AnchorParams(0.0, 5.0, 0.0, 20.0);
            ManeuverParams parameters = TestUtil.Params(minSpeedKn: 2.0, anchor: anchor);
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 0.0, 10.0);

            IReadOnlyList<KinematicState> states = NomotoSimulator.Simulate(
                initial, parameters,
                new[] { Intervention.EmergencyAnchor(0.0, AnchorSide.Both) },
                30.0, 0.05);

            Assert.True(TestUtil.LastState(states).SpeedKn >= 2.0 - 1e-12);
        }

        [Fact]
        public void AnchorSimulationIsBitwiseDeterministic()
        {
            AnchorParams anchor = new AnchorParams(5.0, 0.2, 0.5, 8.0);
            ManeuverParams parameters = TestUtil.Params(anchor: anchor);
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 0.0, 10.0);
            Intervention[] interventions =
            {
                Intervention.EmergencyAnchor(10.0, AnchorSide.Starboard),
                Intervention.TurnStarboard(30.0, 20.0, 20.0),
                Intervention.FullAstern(60.0)
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

        [Fact]
        public void ManeuverParamsCarryDefaultAnchor()
        {
            ManeuverParams parameters = TestUtil.Params(displacementTons: 70000.0);
            Assert.NotNull(parameters.Anchor);
            Assert.Equal(12.0, parameters.Anchor.LetGoToBiteSec);
            Assert.Empty(parameters.Validate());
        }

        private static double SignedHeadingDelta(double heading, double reference)
        {
            double delta = (heading - reference) % 360.0;
            if (delta > 180.0) delta -= 360.0;
            if (delta < -180.0) delta += 360.0;
            return delta;
        }
    }
}

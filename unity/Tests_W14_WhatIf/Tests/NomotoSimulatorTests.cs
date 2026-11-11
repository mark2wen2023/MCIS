using System;
using System.Collections.Generic;
using Xunit;
using Mcis.Simulation.WhatIf;

namespace Mcis.Tests.W14
{
    public class NomotoSimulatorTests
    {
        [Fact]
        public void SteadyTurnRateMatchesKTimesRudder()
        {
            ManeuverParams parameters = TestUtil.Params(
                k: 0.08, t: 80.0, referenceSpeedKn: 10.0, rudderRateDegPerSec: 10.0);
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 0.0, 10.0);

            IReadOnlyList<KinematicState> states = NomotoSimulator.Simulate(
                initial, parameters,
                new[] { Intervention.TurnStarboard(0.0, 10.0, 1000.0) },
                500.0, 0.05);

            KinematicState last = TestUtil.LastState(states);
            double expected = parameters.K * 10.0;
            TestUtil.AssertNear(expected, last.RotDegPerSec, expected * 0.02, "稳态转首率应约为 K·δ");
            Assert.True(last.HeadingDeg > 100.0);
        }

        [Fact]
        public void TurnRateAtTimeConstantIsAboutSixtyThreePercent()
        {
            ManeuverParams parameters = TestUtil.Params(
                k: 0.05, t: 100.0, referenceSpeedKn: 10.0, rudderRateDegPerSec: 10.0);
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 0.0, 10.0);

            IReadOnlyList<KinematicState> states = NomotoSimulator.Simulate(
                initial, parameters,
                new[] { Intervention.TurnStarboard(0.0, 2.0, 170.0) },
                100.0, 0.05);

            double steady = parameters.K * 2.0;
            double expected = steady * (1.0 - Math.Exp(-1.0));
            TestUtil.AssertNear(expected, TestUtil.LastState(states).RotDegPerSec, expected * 0.02,
                "t=T 时一阶响应应达到约 63%");
        }

        [Fact]
        public void RudderRateLimitsRudderMovement()
        {
            ManeuverParams parameters = TestUtil.Params(rudderRateDegPerSec: 2.5);
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 0.0, 8.0);

            IReadOnlyList<KinematicState> atTwo = NomotoSimulator.Simulate(
                initial, parameters,
                new[] { Intervention.TurnStarboard(0.0, 20.0, 170.0) },
                2.0, 0.1);
            IReadOnlyList<KinematicState> atTen = NomotoSimulator.Simulate(
                initial, parameters,
                new[] { Intervention.TurnStarboard(0.0, 20.0, 170.0) },
                10.0, 0.1);

            TestUtil.AssertNear(5.0, TestUtil.LastState(atTwo).RudderDeg, 0.26, "2 s 内舵角应受 2.5°/s 限制");
            TestUtil.AssertNear(20.0, TestUtil.LastState(atTen).RudderDeg, 0.26, "10 s 后应达到指令舵角");
        }

        [Fact]
        public void TurnRateScalesLinearlyWithSpeed()
        {
            ManeuverParams parameters = TestUtil.Params(
                k: 0.08, t: 80.0, referenceSpeedKn: 10.0, rudderRateDegPerSec: 10.0);
            Intervention turn = Intervention.TurnStarboard(0.0, 10.0, 170.0);

            IReadOnlyList<KinematicState> slow = NomotoSimulator.Simulate(
                new KinematicState(0.0, 0.0, 0.0, 0.0, 5.0), parameters, new[] { turn }, 200.0, 0.05);
            IReadOnlyList<KinematicState> fast = NomotoSimulator.Simulate(
                new KinematicState(0.0, 0.0, 0.0, 0.0, 10.0), parameters, new[] { turn }, 200.0, 0.05);

            double slowRate = TestUtil.LastState(slow).RotDegPerSec;
            double fastRate = TestUtil.LastState(fast).RotDegPerSec;
            TestUtil.AssertNear(0.5, slowRate / fastRate, 0.02, "K 随 u/u_ref 线性缩放");
        }

        [Fact]
        public void SpeedDecayFollowsFirstOrderAtTimeConstant()
        {
            ManeuverParams parameters = TestUtil.Params(speedTau: 50.0, minSpeedKn: 0.0);
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 0.0, 10.0);

            IReadOnlyList<KinematicState> states = NomotoSimulator.Simulate(
                initial, parameters,
                new[] { Intervention.ChangeSpeed(0.0, 4.0) },
                50.0, 0.05);

            double speed = TestUtil.LastState(states).SpeedKn;
            double remainingFraction = (speed - 4.0) / (10.0 - 4.0);
            TestUtil.AssertNear(Math.Exp(-1.0), remainingFraction, 0.01, "t=τ 时剩余速度差应约为 37%");
        }

        [Fact]
        public void FullAsternDecaysFasterThanStop()
        {
            ManeuverParams parameters = TestUtil.Params(stopTau: 60.0, asternTau: 20.0);
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 0.0, 10.0);

            IReadOnlyList<KinematicState> stopped = NomotoSimulator.Simulate(
                initial, parameters, new[] { Intervention.Stop(0.0) }, 30.0, 0.05);
            IReadOnlyList<KinematicState> astern = NomotoSimulator.Simulate(
                initial, parameters, new[] { Intervention.FullAstern(0.0) }, 30.0, 0.05);

            Assert.True(TestUtil.LastState(astern).SpeedKn < TestUtil.LastState(stopped).SpeedKn);
            TestUtil.AssertNear(10.0 * Math.Exp(-1.5), TestUtil.LastState(astern).SpeedKn, 0.05);
        }

        [Fact]
        public void SpeedNeverFallsBelowMinimum()
        {
            ManeuverParams parameters = TestUtil.Params(minSpeedKn: 2.0);
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 0.0, 10.0);

            IReadOnlyList<KinematicState> states = NomotoSimulator.Simulate(
                initial, parameters, new[] { Intervention.Stop(0.0) }, 300.0, 0.1);

            Assert.True(TestUtil.LastState(states).SpeedKn >= 2.0 - 1e-12);
            TestUtil.AssertNear(2.0, TestUtil.LastState(states).SpeedKn, 0.1);
        }

        [Fact]
        public void HeadingChangeSettlesWithinOneDegree()
        {
            ManeuverParams parameters = TestUtil.Params(
                k: 0.10, t: 60.0, referenceSpeedKn: 12.0, rudderRateDegPerSec: 2.5);
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 0.0, 8.0);

            IReadOnlyList<KinematicState> states = NomotoSimulator.Simulate(
                initial, parameters,
                new[] { Intervention.TurnStarboard(0.0, 15.0, 30.0) },
                400.0, 0.1);

            KinematicState last = TestUtil.LastState(states);
            Assert.True(TestUtil.HeadingDifference(30.0, last.HeadingDeg) < 1.0,
                "稳向误差应小于 1°，实际 " + last.HeadingDeg);
        }

        [Fact]
        public void ReactionDelayDefersIntervention()
        {
            ManeuverParams parameters = TestUtil.Params(
                k: 0.10, t: 40.0, referenceSpeedKn: 10.0, rudderRateDegPerSec: 2.5);
            KinematicState initial = new KinematicState(0.0, 0.0, 0.0, 0.0, 10.0);
            Intervention turn = Intervention.TurnStarboard(10.0, 15.0, 60.0, 5.0);

            IReadOnlyList<KinematicState> before = NomotoSimulator.Simulate(
                initial, parameters, new[] { turn }, 15.0, 0.1);
            IReadOnlyList<KinematicState> after = NomotoSimulator.Simulate(
                initial, parameters, new[] { turn }, 30.0, 0.1);

            Assert.True(TestUtil.HeadingDifference(0.0, TestUtil.LastState(before).HeadingDeg) < 1e-9);
            Assert.True(TestUtil.HeadingDifference(0.0, TestUtil.LastState(after).HeadingDeg) > 1.0);
        }
    }
}

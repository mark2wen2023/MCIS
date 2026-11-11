using System;
using System.Collections.Generic;
using Mcis.Simulation.WhatIf;
using Xunit;

namespace Mcis.Acceptance.W14
{
    public class NomotoPhysicsAcceptanceTests
    {
        private static ManeuverParams Params(
            double k = 0.10, double t = 60.0, double uRef = 12.0,
            double rudderRate = 2.5, double maxRudder = 35.0)
        {
            return new ManeuverParams(k, t, uRef, maxRudder, rudderRate, 90, 60, 30, 0, 120, 20, 9000);
        }

        [Fact]
        public void SteadyTurnRate_Equals_K_Times_SpeedRatio_Times_Rudder()
        {
            // 独立推导：稳态 T·0 + r = K·(u/u_ref)·δ  ⇒  r = K·(u/u_ref)·δ
            ManeuverParams p = Params();
            double speed = 12.0;
            double rudder = 15.0;
            KinematicState initial = new KinematicState(0, 0, 0, 0, speed, 0, 0);
            IReadOnlyList<KinematicState> states = NomotoSimulator.Simulate(
                initial, p,
                new[] { Intervention.TurnStarboard(0, rudder, 0) },
                600.0, 0.1);

            KinematicState last = states[states.Count - 1];
            double expected = p.K * (speed / p.ReferenceSpeedKn) * rudder;
            Assert.InRange(last.RotDegPerSec, expected - 0.02, expected + 0.02);
            Assert.InRange(last.RudderDeg, rudder - 0.05, rudder + 0.05);
        }

        [Fact]
        public void SteadyTurnRate_ScalesLinearlyWithSpeed()
        {
            ManeuverParams p = Params();
            double r12 = SteadyRate(p, 12.0, 20.0);
            double r6 = SteadyRate(p, 6.0, 20.0);
            Assert.InRange(r6 / r12, 0.48, 0.52);
        }

        [Fact]
        public void StepResponse_AtTimeConstant_IsAbout63PercentOfSteadyRate()
        {
            // 一阶：r(t) = r∞ (1 - e^{-t/T})，t=T 时约为 63.2%
            ManeuverParams p = Params(k: 0.10, t: 40.0, rudderRate: 1000.0);
            KinematicState initial = new KinematicState(0, 0, 0, 0, 12, 0, 0);
            IReadOnlyList<KinematicState> states = NomotoSimulator.Simulate(
                initial, p,
                new[] { Intervention.TurnStarboard(0, 20, 0) },
                200.0, 0.05);

            double rInf = p.K * 20.0;
            KinematicState atT = Sample(states, p.T);
            Assert.InRange(atT.RotDegPerSec / rInf, 0.60, 0.67);
        }

        [Fact]
        public void RudderRateLimit_CapsRudderMovement()
        {
            ManeuverParams p = Params(rudderRate: 2.5, maxRudder: 35);
            KinematicState initial = new KinematicState(0, 0, 0, 0, 10, 0, 0);
            IReadOnlyList<KinematicState> states = NomotoSimulator.Simulate(
                initial, p,
                new[] { Intervention.TurnStarboard(0, 35, 0) },
                20.0, 0.1);

            KinematicState atOne = Sample(states, 1.0);
            Assert.InRange(atOne.RudderDeg, 2.4, 2.6);
            KinematicState atTen = Sample(states, 10.0);
            Assert.True(atTen.RudderDeg < 26.0, "10 s 时舵角不应超过 2.5°/s × 10 s，实际 " + atTen.RudderDeg);
            KinematicState atTwenty = Sample(states, 20.0);
            Assert.InRange(atTwenty.RudderDeg, 34.9, 35.0);
        }

        [Fact]
        public void Simulation_IsBitwiseDeterministic()
        {
            ManeuverParams p = Params();
            KinematicState initial = new KinematicState(0, 10, -20, 15, 9, 0, 0);
            Intervention[] iv = { Intervention.TurnStarboard(5, 20, 25), Intervention.ChangeSpeed(8, 6) };
            IReadOnlyList<KinematicState> a = NomotoSimulator.Simulate(initial, p, iv, 80, 0.1);
            IReadOnlyList<KinematicState> b = NomotoSimulator.Simulate(initial, p, iv, 80, 0.1);
            Assert.Equal(a.Count, b.Count);
            for (int i = 0; i < a.Count; i++)
            {
                W14AccFixture.AssertBitwiseEqual(a[i], b[i]);
            }
        }

        [Fact]
        public void SpeedChange_FollowsFirstOrderTimeConstant()
        {
            ManeuverParams p = Params();
            KinematicState initial = new KinematicState(0, 0, 0, 0, 12, 0, 0);
            IReadOnlyList<KinematicState> states = NomotoSimulator.Simulate(
                initial, p,
                new[] { Intervention.ChangeSpeed(0, 6) },
                300, 0.1);
            // u(t) = 6 + 6 e^{-t/τ}，τ=90，t=90 时应约为 6 + 6*0.3679 = 8.207
            KinematicState atTau = Sample(states, p.SpeedTimeConstantSec);
            Assert.InRange(atTau.SpeedKn, 8.05, 8.35);
        }

        [Fact]
        public void FullAstern_DecaysFasterThanStop()
        {
            ManeuverParams p = Params();
            KinematicState initial = new KinematicState(0, 0, 0, 0, 12, 0, 0);
            double stop = Sample(NomotoSimulator.Simulate(initial, p, new[] { Intervention.Stop(0) }, 60, 0.1), 30).SpeedKn;
            double astern = Sample(NomotoSimulator.Simulate(initial, p, new[] { Intervention.FullAstern(0) }, 60, 0.1), 30).SpeedKn;
            Assert.True(astern < stop - 0.5, "全速后退 30 s 后航速应明显低于停车，astern=" + astern + " stop=" + stop);
        }

        [Fact]
        public void SpeedNeverFallsBelowMinimum()
        {
            ManeuverParams p = new ManeuverParams(0.1, 60, 12, 35, 2.5, 90, 60, 20, 2.0, 100, 16, 5000);
            KinematicState initial = new KinematicState(0, 0, 0, 0, 8, 0, 0);
            IReadOnlyList<KinematicState> states = NomotoSimulator.Simulate(
                initial, p, new[] { Intervention.FullAstern(0) }, 200, 0.1);
            Assert.All(states, s => Assert.True(s.SpeedKn >= 2.0 - 1e-9, "航速低于下限：" + s));
        }

        private static double SteadyRate(ManeuverParams p, double speedKn, double rudderDeg)
        {
            IReadOnlyList<KinematicState> states = NomotoSimulator.Simulate(
                new KinematicState(0, 0, 0, 0, speedKn, 0, 0),
                p,
                new[] { Intervention.TurnStarboard(0, rudderDeg, 0) },
                800, 0.1);
            return states[states.Count - 1].RotDegPerSec;
        }

        private static KinematicState Sample(IReadOnlyList<KinematicState> states, double time)
        {
            for (int i = 0; i < states.Count; i++)
            {
                if (Math.Abs(states[i].TimeSeconds - time) <= 0.06)
                {
                    if (i + 1 < states.Count &&
                        Math.Abs(states[i + 1].TimeSeconds - time) < Math.Abs(states[i].TimeSeconds - time))
                    {
                        return states[i + 1];
                    }
                    return states[i];
                }
            }
            return states[states.Count - 1];
        }
    }
}

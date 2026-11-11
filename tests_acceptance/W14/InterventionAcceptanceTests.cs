using System;
using System.Collections.Generic;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Demo;
using Xunit;

namespace Mcis.Acceptance.W14
{
    public class InterventionAcceptanceTests
    {
        [Fact]
        public void BeforeDivergence_TrackFollowsOriginalExactly()
        {
            WhatIfVessel mary = WhatIfDemoFixture.CreateMary();
            VesselScenario scenario = VesselScenario.Create(
                WhatIfDemoFixture.MaryId,
                Intervention.TurnStarboard(420, 15, 15));
            CounterfactualTrack track = CounterfactualBuilder.Build(mary, scenario, 0.1);

            Assert.True(track.Diverged);
            Assert.Equal(420.0, track.DivergeTimeSeconds, 6);
            for (double t = 0.0; t <= 420.0 + 1e-9; t += 1.0)
            {
                W14AccFixture.AssertBitwiseEqual(mary.SampleAt(t), track.SampleAt(t));
            }
            // 偏离后应离开原航迹
            KinematicState laterOrig = mary.SampleAt(500);
            KinematicState laterCf = track.SampleAt(500);
            double de = laterCf.EastM - laterOrig.EastM;
            double dn = laterCf.NorthM - laterOrig.NorthM;
            Assert.True(Math.Sqrt(de * de + dn * dn) > 10.0, "偏离后航迹应明显离开原航迹");
        }

        [Fact]
        public void EarlierExplicitDiverge_HoldsCourseUntilIntervention()
        {
            WhatIfVessel mary = WhatIfDemoFixture.CreateMary();
            VesselScenario scenario = new VesselScenario(
                WhatIfDemoFixture.MaryId, 300.0,
                new[] { Intervention.TurnStarboard(420, 15, 15) });
            CounterfactualTrack track = CounterfactualBuilder.Build(mary, scenario, 0.1);

            KinematicState at300 = track.SampleAt(300);
            KinematicState at419 = track.SampleAt(419);
            Assert.InRange(at419.HeadingDeg, at300.HeadingDeg - 0.2, at300.HeadingDeg + 0.2);
            Assert.InRange(at419.SpeedKn, at300.SpeedKn - 0.05, at300.SpeedKn + 0.05);
            Assert.True(Math.Abs(KinematicState.NormalizeDeg180(track.SampleAt(520).HeadingDeg - at300.HeadingDeg)) > 5.0);
        }

        [Fact]
        public void SixInterventionKinds_EachChangesTheExpectedState()
        {
            ManeuverParams p = new ManeuverParams(0.10, 40, 12, 35, 5, 80, 50, 25, 0, 120, 20, 9000);
            KinematicState initial = new KinematicState(0, 0, 0, 0, 10, 0, 0);
            const double end = 120.0;

            IReadOnlyList<KinematicState> hold = NomotoSimulator.Simulate(
                initial, p, new[] { Intervention.HoldCourse(0) }, end, 0.1);
            Assert.InRange(hold[hold.Count - 1].HeadingDeg, 0.0, 0.2);
            Assert.InRange(hold[hold.Count - 1].SpeedKn, 9.9, 10.1);

            IReadOnlyList<KinematicState> turn = NomotoSimulator.Simulate(
                initial, p, new[] { Intervention.TurnStarboard(0, 20, 25) }, end, 0.1);
            Assert.InRange(KinematicState.NormalizeDeg180(turn[turn.Count - 1].HeadingDeg - 25), -2.0, 2.0);

            IReadOnlyList<KinematicState> port = NomotoSimulator.Simulate(
                initial, p, new[] { Intervention.TurnPort(0, 20, 25) }, end, 0.1);
            double portDelta = KinematicState.NormalizeDeg180(port[port.Count - 1].HeadingDeg);
            Assert.True(portDelta < -15.0, "左转后航向应变负，实际 " + portDelta);

            IReadOnlyList<KinematicState> slow = NomotoSimulator.Simulate(
                initial, p, new[] { Intervention.ChangeSpeed(0, 6) }, end, 0.1);
            Assert.True(slow[slow.Count - 1].SpeedKn < 8.5 && slow[slow.Count - 1].SpeedKn > 5.5);

            IReadOnlyList<KinematicState> stop = NomotoSimulator.Simulate(
                initial, p, new[] { Intervention.Stop(0) }, end, 0.1);
            IReadOnlyList<KinematicState> astern = NomotoSimulator.Simulate(
                initial, p, new[] { Intervention.FullAstern(0) }, end, 0.1);
            Assert.True(stop[stop.Count - 1].SpeedKn < 4.0);
            Assert.True(astern[astern.Count - 1].SpeedKn < stop[stop.Count - 1].SpeedKn);
        }

        [Fact]
        public void ReactionDelay_DefersExecution()
        {
            ManeuverParams p = ManeuverParams.Default(100, 16, 5000);
            KinematicState initial = new KinematicState(0, 0, 0, 0, 10, 0, 0);
            IReadOnlyList<KinematicState> states = NomotoSimulator.Simulate(
                initial, p,
                new[] { Intervention.TurnStarboard(10, 20, 20, reactionDelaySec: 5) },
                40, 0.1);

            KinematicState before = Find(states, 14.9);
            KinematicState after = Find(states, 16.0);
            Assert.InRange(before.RudderDeg, -0.05, 0.05);
            Assert.True(after.RudderDeg > 1.0, "执行后舵角应开始增加，实际 " + after.RudderDeg);
        }

        [Fact]
        public void EmergencyAnchor_NoEffectBeforeBiteDelay()
        {
            ManeuverParams p = new ManeuverParams(
                0.1, 60, 12, 35, 2.5, 90, 60, 30, 0, 100, 16, 70000,
                new AnchorParams(12, 0.08, 0.30, 6));
            KinematicState initial = new KinematicState(0, 0, 0, 0, 8, 0, 0);
            IReadOnlyList<KinematicState> none = NomotoSimulator.Simulate(
                initial, p, Array.Empty<Intervention>(), 12, 0.1);
            IReadOnlyList<KinematicState> anchor = NomotoSimulator.Simulate(
                initial, p, new[] { Intervention.EmergencyAnchor(0, AnchorSide.Starboard) }, 12, 0.1);
            Assert.Equal(none.Count, anchor.Count);
            for (int i = 0; i < none.Count; i++)
            {
                if (none[i].TimeSeconds <= 12.0 - 1e-6)
                {
                    W14AccFixture.AssertBitwiseEqual(none[i], anchor[i]);
                }
            }
        }

        [Fact]
        public void EmergencyAnchor_AfterBite_DeceleratesAndStarboardYawsRight()
        {
            ManeuverParams p = new ManeuverParams(
                0.1, 60, 12, 35, 2.5, 90, 60, 30, 0, 100, 16, 70000,
                new AnchorParams(12, 0.08, 0.30, 20));
            KinematicState initial = new KinematicState(0, 0, 0, 0, 8, 0, 0);
            IReadOnlyList<KinematicState> none = NomotoSimulator.Simulate(
                initial, p, Array.Empty<Intervention>(), 80, 0.1);
            IReadOnlyList<KinematicState> stb = NomotoSimulator.Simulate(
                initial, p, new[] { Intervention.EmergencyAnchor(0, AnchorSide.Starboard) }, 80, 0.1);
            IReadOnlyList<KinematicState> port = NomotoSimulator.Simulate(
                initial, p, new[] { Intervention.EmergencyAnchor(0, AnchorSide.Port) }, 80, 0.1);
            IReadOnlyList<KinematicState> both = NomotoSimulator.Simulate(
                initial, p, new[] { Intervention.EmergencyAnchor(0, AnchorSide.Both) }, 80, 0.1);

            double t = 80.0;
            Assert.True(Find(stb, t).SpeedKn < Find(none, t).SpeedKn - 1.0,
                "抓底后应明显减速");
            Assert.True(KinematicState.NormalizeDeg180(Find(stb, t).HeadingDeg) > 5.0,
                "右锚应向右转首");
            Assert.True(KinematicState.NormalizeDeg180(Find(port, t).HeadingDeg) < -5.0,
                "左锚应向左转首");
            Assert.InRange(KinematicState.NormalizeDeg180(Find(both, t).HeadingDeg), -0.5, 0.5);
            Assert.InRange(Find(both, t).SpeedKn, Find(stb, t).SpeedKn - 0.2, Find(stb, t).SpeedKn + 0.2);
        }

        [Fact]
        public void EmergencyAnchor_HighSpeed_ReducesDeceleration()
        {
            // 超过 MaxEffectiveSpeedKn 后按 v_max/u 折减
            AnchorParams anchor = new AnchorParams(0.0, 0.20, 0.0, 6.0);
            ManeuverParams p = new ManeuverParams(0.1, 60, 12, 35, 2.5, 1e6, 1e6, 1e6, 0, 100, 16, 70000, anchor);
            // 用很大的速度时间常数，使主机几乎不改变航速，便于观察锚减速度
            KinematicState slow = new KinematicState(0, 0, 0, 0, 5.0, 0, 0);
            KinematicState fast = new KinematicState(0, 0, 0, 0, 12.0, 0, 0);
            Intervention drop = Intervention.EmergencyAnchor(0, AnchorSide.Both);
            double slowAfter = Find(NomotoSimulator.Simulate(slow, p, new[] { drop }, 10, 0.1), 10).SpeedKn;
            double fastAfter = Find(NomotoSimulator.Simulate(fast, p, new[] { drop }, 10, 0.1), 10).SpeedKn;
            double slowDrop = 5.0 - slowAfter;
            double fastDrop = 12.0 - fastAfter;
            // 5 kn < 6 kn：满效果，约 0.20*10=2.0 kn；12 kn：折减 6/12=0.5，约 1.0 kn
            Assert.InRange(slowDrop, 1.7, 2.2);
            Assert.InRange(fastDrop, 0.8, 1.3);
            Assert.True(fastDrop < slowDrop, "超速时应减速更弱");
        }

        [Fact]
        public void EmergencyAnchor_KnownIssue_YawContinuesNearZeroSpeed()
        {
            // W14.1：锚转首随航速衰减，船停下后转首为 0。
            AnchorParams anchor = new AnchorParams(0.0, 0.5, 0.30, 20);
            ManeuverParams p = new ManeuverParams(0.1, 60, 12, 35, 2.5, 90, 60, 10, 0, 100, 16, 70000, anchor);
            KinematicState initial = new KinematicState(0, 0, 0, 0, 3, 0, 0);
            IReadOnlyList<KinematicState> states = NomotoSimulator.Simulate(
                initial, p, new[] { Intervention.EmergencyAnchor(0, AnchorSide.Starboard) }, 80, 0.1);
            KinematicState later = Find(states, 80);
            bool foundStop = false;
            KinematicState almostStop = later;
            foreach (KinematicState s in states)
            {
                if (s.SpeedKn <= 0.05)
                {
                    almostStop = s;
                    foundStop = true;
                    break;
                }
            }
            Assert.True(foundStop, "80 s 内航速未降到 0.05 kn 以下，无法确认停船后转首");
            double yawAfterStop = KinematicState.NormalizeDeg180(later.HeadingDeg - almostStop.HeadingDeg);
            Assert.True(Math.Abs(yawAfterStop) <= 0.05,
                "停船后转首应为 0，实际继续改变 " + yawAfterStop.ToString("F4") +
                "°（t_stop=" + almostStop.TimeSeconds + "）");
        }

        private static KinematicState Find(IReadOnlyList<KinematicState> states, double time)
        {
            KinematicState best = states[0];
            double bestAbs = Math.Abs(best.TimeSeconds - time);
            for (int i = 1; i < states.Count; i++)
            {
                double a = Math.Abs(states[i].TimeSeconds - time);
                if (a < bestAbs)
                {
                    best = states[i];
                    bestAbs = a;
                }
            }
            return best;
        }
    }
}

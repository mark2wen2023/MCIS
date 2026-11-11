using System;
using System.Collections.Generic;
using Mcis.Simulation.Damage;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Demo;
using Xunit;

namespace Mcis.Acceptance.W14
{
    public class DemoBoundaryAcceptanceTests
    {
        [Fact]
        public void DemoReportedNumbers_MatchImplementerAnnouncement()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<ScenarioResult> results = ScenarioEvaluator.EvaluateAll(setup, WhatIfDemoFixture.Scenarios());
            ScenarioResult s0 = results[0];
            ScenarioResult s1 = results[1];
            ScenarioResult s2 = results[2];
            ScenarioResult s3 = results[3];

            Assert.Equal("S0", s0.ScenarioId);
            Assert.Equal(ScenarioVerdict.Collision, s0.Verdict);
            Assert.Equal("碰撞", s0.VerdictText);
            Assert.True(s0.TcSeconds.HasValue);
            // 14:15:00 + 539.96 s = 14:23:59.96
            Assert.InRange(s0.TcSeconds.Value, 539.90, 540.05);
            Assert.Equal("14:23:59.96", s0.TcLocalText);

            Assert.Equal(ScenarioVerdict.NearMiss, s1.Verdict);
            Assert.Equal("险情", s1.VerdictText);
            Assert.False(s1.Collision);
            Assert.InRange(s1.MinClearanceM, 120.0, 135.0);

            Assert.Equal(ScenarioVerdict.Collision, s2.Verdict);
            Assert.True(s2.Collision);

            Assert.Equal(ScenarioVerdict.NearMiss, s3.Verdict);
            Assert.False(s3.Collision);
            Assert.InRange(s3.MinClearanceM, 45.0, 60.0);
        }

        [Fact]
        public void Evaluation_IsBitwiseDeterministic()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            WhatIfScenario s1 = WhatIfDemoFixture.Scenarios()[1];
            ScenarioResult a = ScenarioEvaluator.Evaluate(setup, s1);
            ScenarioResult b = ScenarioEvaluator.Evaluate(setup, s1);
            Assert.Equal(a.MinDistanceNm, b.MinDistanceNm);
            Assert.Equal(a.MinClearanceM, b.MinClearanceM);
            Assert.Equal(a.MinDcpaNm, b.MinDcpaNm);
            Assert.Equal(a.Collision, b.Collision);
            Assert.Equal(a.TcSeconds, b.TcSeconds);
            Assert.Equal(a.Verdict, b.Verdict);
            foreach (double t in new[] { 0.0, 200.0, 420.0, 500.0, 700.0 })
            {
                W14AccFixture.AssertBitwiseEqual(
                    a.Tracks[WhatIfDemoFixture.MaryId].SampleAt(t),
                    b.Tracks[WhatIfDemoFixture.MaryId].SampleAt(t));
            }
        }

        [Fact]
        public void ParallelSameDirection_NoCollision()
        {
            WhatIfVessel a = W14AccFixture.StraightVessel("A", 0, 0, 0, 10, 120, 20, 0, 300);
            WhatIfVessel b = W14AccFixture.StraightVessel("B", 200, 0, 0, 10, 100, 16, 0, 300);
            ScenarioResult result = ScenarioEvaluator.Evaluate(
                W14AccFixture.TwoShipSetup(a, b, 0, 300), WhatIfScenario.Original());
            Assert.False(result.Collision);
            Assert.Null(result.TcSeconds);
            Assert.Null(result.Geometry);
            Assert.NotEqual(ScenarioVerdict.Collision, result.Verdict);
            Assert.True(result.MinClearanceM > 50.0, "平行同向横距约 200 m，净距应明显为正，实际 " + result.MinClearanceM);
        }

        [Fact]
        public void NoEncounter_DivergingCourses_Avoided()
        {
            WhatIfVessel a = W14AccFixture.StraightVessel("A", 0, 0, 0, 10, 120, 20, 0, 400);
            WhatIfVessel b = W14AccFixture.StraightVessel("B", 2000, 0, 90, 10, 100, 16, 0, 400);
            ScenarioResult result = ScenarioEvaluator.Evaluate(
                W14AccFixture.TwoShipSetup(a, b, 0, 400), WhatIfScenario.Original());
            Assert.False(result.Collision);
            Assert.Equal(ScenarioVerdict.Avoided, result.Verdict);
            Assert.True(result.MinClearanceM > W14AccFixture.MetersPerNm * 0.1);
        }

        [Fact]
        public void Dt_0_1_And_0_05_SameVerdictForDemoScenarios()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<WhatIfScenario> scenarios = WhatIfDemoFixture.Scenarios();
            foreach (WhatIfScenario scenario in scenarios)
            {
                ScenarioVerdict a = VerdictAtStep(setup, scenario, 0.1);
                ScenarioVerdict b = VerdictAtStep(setup, scenario, 0.05);
                Assert.Equal(a, b);
            }
        }

        [Fact]
        public void NullScenario_EvaluatesAsOriginal()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            ScenarioResult explicitS0 = ScenarioEvaluator.Evaluate(setup, WhatIfScenario.Original());
            ScenarioResult implicitS0 = ScenarioEvaluator.Evaluate(setup, null);
            Assert.Equal(explicitS0.Collision, implicitS0.Collision);
            Assert.Equal(explicitS0.TcSeconds, implicitS0.TcSeconds);
            Assert.Equal(explicitS0.Verdict, implicitS0.Verdict);
        }

        private static ScenarioVerdict VerdictAtStep(WhatIfSetup setup, WhatIfScenario scenario, double step)
        {
            CounterfactualTrack own = CounterfactualBuilder.Build(
                setup.FindVessel(setup.OwnVesselId),
                scenario == null ? null : scenario.FindVessel(setup.OwnVesselId),
                step);
            CounterfactualTrack tgt = CounterfactualBuilder.Build(
                setup.FindVessel(setup.TargetVesselId),
                scenario == null ? null : scenario.FindVessel(setup.TargetVesselId),
                step);

            var contact = CollisionDetector.FindFirstContactTime(
                t => own.ToBodyState(t),
                t => tgt.ToBodyState(t),
                new Mcis.Core.SimTime(setup.StartSeconds),
                new Mcis.Core.SimTime(setup.EndSeconds),
                setup.CollisionPrecisionSec,
                setup.CollisionCoarseStepSec);
            if (contact.HasValue) return ScenarioVerdict.Collision;

            double bestTime = setup.StartSeconds;
            double bestCenter = double.PositiveInfinity;
            for (double t = setup.StartSeconds; t <= setup.EndSeconds + 1e-9; t += 1.0)
            {
                KinematicState sa = own.SampleAt(t);
                KinematicState sb = tgt.SampleAt(t);
                double de = sb.EastM - sa.EastM;
                double dn = sb.NorthM - sa.NorthM;
                double d = Math.Sqrt(de * de + dn * dn);
                if (d < bestCenter)
                {
                    bestCenter = d;
                    bestTime = t;
                }
            }
            double clearance = OrientedBoundingBox.Clearance(
                W14AccFixture.BoxOf(own.SampleAt(bestTime), own.LoaM, own.BeamM),
                W14AccFixture.BoxOf(tgt.SampleAt(bestTime), tgt.LoaM, tgt.BeamM));
            if (clearance < 0) clearance = 0;
            return clearance < setup.SafeDistanceM ? ScenarioVerdict.NearMiss : ScenarioVerdict.Avoided;
        }
    }
}

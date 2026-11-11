using System;
using System.Collections.Generic;
using Xunit;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Simulation.Cpa;
using Mcis.Simulation.Damage;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Demo;

namespace Mcis.Tests.W14
{
    public class ScenarioEvaluatorTests
    {
        [Fact]
        public void S0CollidesNearFiveFortyAndStrikesLilyPortSide()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<WhatIfScenario> scenarios = WhatIfDemoFixture.Scenarios();
            ScenarioResult s0 = ScenarioEvaluator.Evaluate(setup, scenarios[0]);

            Assert.True(s0.Collision);
            Assert.NotNull(s0.TcSeconds);
            Assert.InRange(s0.TcSeconds.Value, 510.0, 570.0);
            Assert.StartsWith("14:2", s0.TcLocalText);
            Assert.Equal(ScenarioVerdict.Collision, s0.Verdict);
            Assert.Equal("碰撞", s0.VerdictText);

            CounterfactualTrack mary = s0.Tracks[WhatIfDemoFixture.MaryId];
            CounterfactualTrack lily = s0.Tracks[WhatIfDemoFixture.LilyId];
            double tc = s0.TcSeconds.Value;
            KinematicState m = mary.SampleAt(tc);
            KinematicState l = lily.SampleAt(tc);

            double rad = l.HeadingDeg * Math.PI / 180.0;
            double starboardEast = Math.Cos(rad);
            double starboardNorth = -Math.Sin(rad);
            double side = (m.EastM - l.EastM) * starboardEast + (m.NorthM - l.NorthM) * starboardNorth;
            Assert.True(side < 0.0, "Mary 应位于 Lily 左舷一侧");

            double mrad = m.HeadingDeg * Math.PI / 180.0;
            double forwardEast = Math.Sin(mrad);
            double forwardNorth = Math.Cos(mrad);
            double toLilyEast = l.EastM - m.EastM;
            double toLilyNorth = l.NorthM - m.NorthM;
            double bowDot = toLilyEast * forwardEast + toLilyNorth * forwardNorth;
            double distance = Math.Sqrt(toLilyEast * toLilyEast + toLilyNorth * toLilyNorth);
            Assert.True(bowDot > distance * 0.9, "碰撞点应位于 Mary 船首方向");

            OrientedBoundingBox maryBox = mary.ToBodyState(tc).Obb;
            OrientedBoundingBox lilyBox = lily.ToBodyState(tc).Obb;
            Assert.True(OrientedBoundingBox.Clearance(maryBox, lilyBox) <= 1e-6);
        }

        [Fact]
        public void S1AvoidsCollisionAndIncreasesMinimumDistance()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<WhatIfScenario> scenarios = WhatIfDemoFixture.Scenarios();
            ScenarioResult s0 = ScenarioEvaluator.Evaluate(setup, scenarios[0]);
            ScenarioResult s1 = ScenarioEvaluator.Evaluate(setup, scenarios[1]);

            Assert.False(s1.Collision);
            Assert.Null(s1.TcSeconds);
            Assert.Equal("—", s1.TcLocalText);
            Assert.True(s1.MinClearanceM > 0.0, "S1 未碰撞，OBB 净距应为正");
            Assert.True(s1.MinDistanceNm > s0.MinDistanceNm + 0.05,
                "S1 最小距离应明显大于 S0，实际 " + s1.MinDistanceNm + " vs " + s0.MinDistanceNm);
            Assert.NotEqual(ScenarioVerdict.Collision, s1.Verdict);
        }

        [Fact]
        public void ResultsCarryAssumptionsAndDisclaimer()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            ScenarioResult result = ScenarioEvaluator.Evaluate(setup, WhatIfDemoFixture.Scenarios()[2]);

            Assert.NotEmpty(result.Assumptions);
            Assert.Contains(result.Assumptions, a => a.Contains("Nomoto"));
            Assert.Contains(result.Assumptions, a => a.Contains("OBB"));
            Assert.Equal(WhatIfAssumptions.DisclaimerText, result.Disclaimer);
            Assert.Contains("仅供分析参考", result.Disclaimer);
            Assert.Contains("不作责任认定", result.Disclaimer);
            Assert.NotEmpty(result.VerdictText);
        }

        [Fact]
        public void CpaMatchesDirectCpaServiceConstruction()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            ScenarioResult result = ScenarioEvaluator.Evaluate(setup, WhatIfDemoFixture.Scenarios()[1]);
            CounterfactualTrack own = result.Tracks[setup.OwnVesselId];
            CounterfactualTrack target = result.Tracks[setup.TargetVesselId];

            CpaService direct = new CpaService(
                t => own.ToMotionState(t),
                t => target.ToMotionState(t),
                setup.StartSeconds,
                setup.EndSeconds,
                setup.CpaStepSeconds,
                setup.Thresholds,
                setup.OwnVesselId,
                setup.TargetVesselId);
            CpaTimeSeries series = direct.PrimarySeries;

            Assert.Equal(result.MinDistanceNm, series.MinDistanceNm);
            Assert.Equal(result.MinDistanceTimeSeconds, series.MinDistanceTime.Seconds);
            Assert.Equal(result.MinDcpaNm, series.MinDcpaSample.DcpaNm);
            Assert.Equal(result.Cpa.Samples.Count, series.Samples.Count);
        }

        [Fact]
        public void CollisionTimeMatchesDirectCollisionDetector()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            ScenarioResult result = ScenarioEvaluator.Evaluate(setup, WhatIfDemoFixture.Scenarios()[0]);
            CounterfactualTrack own = result.Tracks[setup.OwnVesselId];
            CounterfactualTrack target = result.Tracks[setup.TargetVesselId];

            SimTime? direct = CollisionDetector.FindFirstContactTime(
                t => own.ToBodyState(t),
                t => target.ToBodyState(t),
                new SimTime(setup.StartSeconds),
                new SimTime(setup.EndSeconds),
                setup.CollisionPrecisionSec,
                setup.CollisionCoarseStepSec);

            Assert.True(direct.HasValue);
            Assert.True(result.TcSeconds.HasValue);
            Assert.Equal(result.TcSeconds.Value, direct.Value.Seconds);
        }

        [Fact]
        public void EvaluationIsBitwiseDeterministic()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            WhatIfScenario scenario = WhatIfDemoFixture.Scenarios()[1];

            ScenarioResult first = ScenarioEvaluator.Evaluate(setup, scenario);
            ScenarioResult second = ScenarioEvaluator.Evaluate(setup, scenario);

            Assert.Equal(first.MinDistanceNm, second.MinDistanceNm);
            Assert.Equal(first.MinDcpaNm, second.MinDcpaNm);
            Assert.Equal(first.MinClearanceM, second.MinClearanceM);
            Assert.Equal(first.Collision, second.Collision);
            double[] times = { 400.0, 450.0, 500.0, 540.0, 600.0, 720.0 };
            for (int i = 0; i < times.Length; i++)
            {
                Assert.Equal(
                    first.Tracks[setup.OwnVesselId].SampleAt(times[i]),
                    second.Tracks[setup.OwnVesselId].SampleAt(times[i]));
                Assert.Equal(
                    first.Tracks[setup.TargetVesselId].SampleAt(times[i]),
                    second.Tracks[setup.TargetVesselId].SampleAt(times[i]));
            }
        }

        [Fact]
        public void EvaluateAllReturnsFourScenarios()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<ScenarioResult> results =
                ScenarioEvaluator.EvaluateAll(setup, WhatIfDemoFixture.Scenarios());

            Assert.Equal(4, results.Count);
            Assert.Equal("S0", results[0].ScenarioId);
            Assert.Equal("S1", results[1].ScenarioId);
            Assert.Equal("S2", results[2].ScenarioId);
            Assert.Equal("S3", results[3].ScenarioId);
        }

        [Fact]
        public void NullScenarioEvaluatesAsOriginal()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            ScenarioResult result = ScenarioEvaluator.Evaluate(setup, null);

            Assert.Equal("S0", result.ScenarioId);
            Assert.True(result.Tracks[setup.OwnVesselId].Diverged == false);
            Assert.True(result.Collision);
        }

        [Fact]
        public void UnknownScenarioVesselThrows()
        {
            WhatIfSetup setup = WhatIfDemoFixture.CreateSetup();
            WhatIfScenario scenario = new WhatIfScenario(
                "S9", "未知船", "引用不存在的船",
                new[] { VesselScenario.Create("Nobody", Intervention.Stop(10.0)) });

            Assert.Throws<ArgumentException>(() => ScenarioEvaluator.Evaluate(setup, scenario));
        }
    }
}

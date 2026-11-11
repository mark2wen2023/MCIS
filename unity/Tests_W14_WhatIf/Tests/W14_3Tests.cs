using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Xunit;
using Xunit.Abstractions;
using Mcis.Domain.Common;
using Mcis.Simulation.Damage;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Cases;

namespace Mcis.Tests.W14
{
    public class W14_3Tests
    {
        private readonly ITestOutputHelper output;
        public W14_3Tests(ITestOutputHelper output) { this.output = output; }

        [Fact]
        public void NarrowValley_AgreesWithIndependentHundredthSecondScan()
        {
            var ownStates = new List<KinematicState>();
            var targetStates = new List<KinematicState>();
            for (int i = 0; i <= 200; i++)
            {
                double t = i * 0.1;
                double offset = Math.Abs(t - 6.25);
                double dip = offset <= 0.12 ? 55 * (1 - offset / 0.12) : 0;
                ownStates.Add(new KinematicState(t, 0, 0, 0, 0));
                targetStates.Add(new KinematicState(t, 50 - dip, 200 - 8 * t, 180, 8));
            }
            var own = WhatIfVessel.FromStates("Own", ManeuverParams.Default(200, 20, 8000), ownStates);
            var target = WhatIfVessel.FromStates("Target", ManeuverParams.Default(80, 16, 5000), targetStates);
            var setup = new WhatIfSetup(new[] { own, target }, "Own", "Target", 0, 20, cpaStepSeconds: 0.1);
            var result = ScenarioEvaluator.Evaluate(setup, WhatIfScenario.Original());
            double truth = double.PositiveInfinity;
            for (int i = 0; i <= 2000; i++)
            {
                double t = i * 0.01;
                truth = Math.Min(truth, OrientedBoundingBox.Clearance(Box(result.Tracks["Own"], t), Box(result.Tracks["Target"], t)));
            }
            output.WriteLine("reported={0:R}; brute0.01={1:R}; time={2:R}", result.MinClearanceM, truth, result.MinClearanceTimeSeconds);
            Assert.False(result.Collision);
            Assert.True(truth < 20);
            Assert.True(Math.Abs(result.MinClearanceM - truth) <= 0.1,
                "D06: reported=" + result.MinClearanceM.ToString("R") + "; brute=" + truth.ToString("R"));
        }

        [Theory]
        [InlineData(0.4999999, false)]
        [InlineData(0.5, false)]
        [InlineData(0.5000001, true)]
        [InlineData(-0.5000001, true)]
        public void HighTurnThresholdUsesMagnitudeAndStrictNumericalBoundary(double rate, bool expected)
        {
            Assert.Equal(expected, ScenarioEvaluator.HighTurnInterval(
                new KinematicState(0, 0, 0, 0, 0, rate), new KinematicState(1, 0, 0, 0, 0)));
        }

        [Theory]
        [InlineData(359.98, 0.04, true)]
        [InlineData(359.98, 0.02, false)]
        [InlineData(0.04, 359.98, true)]
        public void MissingRotStillDetectsWrappedHeadingRate(double a, double b, bool expected)
        {
            Assert.Equal(expected, ScenarioEvaluator.HighTurnInterval(
                new KinematicState(0, 0, 0, a, 0), new KinematicState(0.1, 0, 0, b, 0)));
        }

        [Fact]
        public void GridIncludesActualOffsetKnotsAndExactEndpoints()
        {
            var p = ManeuverParams.Default(100, 16, 5000);
            var a = new CounterfactualTrack("a", 0.1, new[] { 0.0, 0.037, 0.137, 0.237, 0.3 }
                .Select(t => new KinematicState(t, 0, 0, 0, 0)).ToArray(), true, 0, p, null);
            var b = new CounterfactualTrack("b", 0.1, new[] { 0.0, 0.011, 0.111, 0.211, 0.3 }
                .Select(t => new KinematicState(t, 100, 0, 0, 0)).ToArray(), true, 0, p, null);
            var times = ScenarioEvaluator.ClearanceSamplingTimes(0, 0.3, a, b);
            foreach (var state in a.States.Concat(b.States)) Assert.Contains(state.TimeSeconds, times);
            Assert.Contains(0.1, times); Assert.Contains(0.2, times);
            Assert.Equal(0, times[0]); Assert.Equal(0.3, times.Last());
            Assert.Equal(new[] { 0.0, 1e-10 }, ScenarioEvaluator.ClearanceSamplingTimes(0, 1e-10, a, b));
        }

        [Fact]
        public void ForcedTurningIntervalCatchesValleyWithoutCoarseLocalMinimum()
        {
            Func<double, double> f = t => 100 - t - 20 * Math.Max(0, 1 - Math.Abs(t - 0.05) / 0.02);
            double t;
            double unrefined = ScenarioEvaluator.MinimumOnGrid(new[] { 0.0, 0.1, 0.2 }, f, 0.01, null, out t);
            double refined = ScenarioEvaluator.MinimumOnGrid(new[] { 0.0, 0.1, 0.2 }, f, 0.01,
                (a, b) => a < 0.1, out t);
            Assert.True(unrefined > 99);
            Assert.InRange(Math.Abs(refined - 79.95), 0, 0.001);
            Assert.InRange(t, 0.049, 0.051);
        }

        [Theory]
        [InlineData(0)]
        [InlineData(1)]
        [InlineData(2)]
        public void EndpointPlateauAndMultipleValleysAreCovered(int kind)
        {
            Func<double, double> f = kind == 0 ? t => t : kind == 1 ? t => 7 :
                t => Math.Min((t - 0.22) * (t - 0.22) + 1, (t - 0.77) * (t - 0.77));
            double t;
            double best = ScenarioEvaluator.GlobalMinimum(0, 1, f, 0.1, 0.01, out t);
            Assert.InRange(Math.Abs(best - (kind == 1 ? 7 : 0)), 0, 1e-6);
        }

        private static OrientedBoundingBox Box(CounterfactualTrack track, double t)
        {
            var state = track.SampleAt(t);
            return OrientedBoundingBox.FromVessel(new EnuPosition(state.EastM, state.NorthM, 0),
                state.HeadingDeg, (float)track.LoaM, (float)track.BeamM);
        }

        [Fact]
        public void CaptureCurrentYangzeForBeforeAfterGate()
        {
            var result = Yangze22Case.Run(Yangze22TestData.ReadTrackLines(), Yangze22CaseTests.LoadInputs());
            var snapshot = new {
                origin = "Actual Yangze22Case.Run from current compiled sources, not fixture/seed readback",
                rows = result.Results.Select(r => new {
                    r.ScenarioId, r.MinClearanceM, r.MinClearanceTimeSeconds, r.Collision,
                    r.TcSeconds, r.TcLocalText, Verdict = r.Verdict.ToString(),
                    r.MinDistanceNm, r.MinDcpaNm,
                    geometry = r.Geometry == null ? null : new {
                        r.Geometry.CollisionAngleDeg, r.Geometry.StrikingVesselId,
                        r.Geometry.StruckVesselId, r.Geometry.StruckSide,
                        r.Geometry.ContactFromStruckBowM, r.Geometry.IsBowToBow }
                }).ToArray(),
                comparison = result.Comparison.Rows.Select(r => new {
                    r.ScenarioId, r.IsCritical, r.CriticalReason, r.DisplayVerdictText,
                    r.SensitivityRangeText, sensitivity = r.Sensitivity.Select(s => new {
                        s.Label, s.Collision, Verdict = s.Verdict.ToString(), s.MinClearanceM }).ToArray()
                }).ToArray(),
                antenna = result.AntennaSensitivity
            };
            var json = JsonSerializer.Serialize(snapshot, new JsonSerializerOptions { WriteIndented = true });
            output.WriteLine(json);
            var path = Environment.GetEnvironmentVariable("MCIS_W143_SNAPSHOT_PATH");
            if (!string.IsNullOrEmpty(path)) File.WriteAllText(path, json + "\n");
            Assert.Equal(5, result.Results.Count);
        }
    }
}

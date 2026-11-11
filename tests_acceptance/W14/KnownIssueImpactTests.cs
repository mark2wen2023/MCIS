using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using Mcis.Simulation.Damage;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Cases;
using Mcis.Simulation.WhatIf.Demo;
using Xunit;

namespace Mcis.Acceptance.W14
{
    /// <summary>量化实施方已知问题的影响，默认通过；结果写入 logs/。</summary>
    public class KnownIssueImpactTests
    {
        [Fact]
        public void RecordSatVersusTrueClearanceForNearMissScenarios()
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("scenario,verdict,satClearanceM,trueClearanceM,safeM,satWouldFlip");
            WhatIfSetup demo = WhatIfDemoFixture.CreateSetup();
            IReadOnlyList<ScenarioResult> demoResults = ScenarioEvaluator.EvaluateAll(demo, WhatIfDemoFixture.Scenarios());
            foreach (ScenarioResult r in demoResults)
            {
                Append(sb, "demo-" + r.ScenarioId, r);
            }
            Yangze22Result yangze = Yangze22Case.Run(
                W14AccFixture.ReadYangzeTrackLines(), W14AccFixture.LoadYangzeInputs());
            foreach (ScenarioResult r in yangze.Results)
            {
                Append(sb, "yangze-" + r.ScenarioId, r);
            }
            string path = Path.Combine(W14AccFixture.LogsDirectory, "w14-clearance-sat-vs-true.csv");
            File.WriteAllText(path, sb.ToString(), Encoding.UTF8);
            Assert.True(File.Exists(path));
        }

        private static void Append(StringBuilder sb, string name, ScenarioResult r)
        {
            if (r.Collision)
            {
                sb.AppendLine(name + "," + r.Verdict + ",0,0,,false");
                return;
            }
            CounterfactualTrack own = null, tgt = null;
            foreach (KeyValuePair<string, CounterfactualTrack> kv in r.Tracks)
            {
                if (own == null) own = kv.Value;
                else tgt = kv.Value;
            }
            double t = r.MinDistanceTimeSeconds;
            // evaluate at a refined closest-approach neighbourhood
            double bestTrue = double.PositiveInfinity;
            double bestSat = double.PositiveInfinity;
            for (double tau = t - 2; tau <= t + 2; tau += 0.02)
            {
                KinematicState a = own.SampleAt(tau);
                KinematicState b = tgt.SampleAt(tau);
                OrientedBoundingBox ba = W14AccFixture.BoxOf(a, own.LoaM, own.BeamM);
                OrientedBoundingBox bb = W14AccFixture.BoxOf(b, tgt.LoaM, tgt.BeamM);
                double sat = OrientedBoundingBox.Clearance(ba, bb);
                double truth = W14AccFixture.TrueObbDistance(ba, bb);
                if (truth < bestTrue)
                {
                    bestTrue = truth;
                    bestSat = sat;
                }
            }
            bool flip = r.Verdict == ScenarioVerdict.NearMiss && bestTrue >= 185.2
                        || r.Verdict == ScenarioVerdict.Avoided && bestTrue < 185.2;
            sb.AppendLine(string.Format(
                CultureInfo.InvariantCulture,
                "{0},{1},{2:F2},{3:F2},185.20,{4}",
                name, r.Verdict, r.MinClearanceM, bestTrue, flip ? "true" : "false"));
            // also keep bestSat used
            _ = bestSat;
        }

        [Fact]
        public void Y5_TrueClearanceCrossesSafeLine_VerdictShouldBeAvoided()
        {
            // W14.1：D02 已修。默认设定（截断+天线）Y5 为无碰撞，约 239.1 m；
            // 只修 OBB（不截断、天线视为船中）约 361 m。
            Yangze22Result yangze = Yangze22Case.Run(
                W14AccFixture.ReadYangzeTrackLines(), W14AccFixture.LoadYangzeInputs());
            ScenarioResult y5 = yangze.Find("Y5");
            Assert.False(y5.Collision);
            Assert.Equal(ScenarioVerdict.Avoided, y5.Verdict);
            Assert.InRange(y5.MinClearanceM, 230.0, 250.0);

            string[] lines = W14AccFixture.ReadYangzeTrackLines();
            Yangze22Inputs noAntennaNoTrunc = W14AccFixture.LoadYangzeInputs(300.0, false);
            Yangze22Study obbOnly = Yangze22Case.Build(lines, noAntennaNoTrunc, 0.0, 0.0);
            ScenarioResult y5Obb = null;
            foreach (ScenarioResult r in obbOnly.EvaluateAll())
            {
                if (r.ScenarioId == "Y5") y5Obb = r;
            }
            Assert.NotNull(y5Obb);
            Assert.False(y5Obb.Collision);
            Assert.Equal(ScenarioVerdict.Avoided, y5Obb.Verdict);
            Assert.InRange(y5Obb.MinClearanceM, 350.0, 375.0);
        }
    }
}
